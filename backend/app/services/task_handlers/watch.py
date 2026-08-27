"""观看任务：真实间隔心跳上报，累计观看满 5 分钟（300 秒），拿满 +5 经验。"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from app.exceptions import BiliAPIException, TaskExecuteException
from app.services.anti_detect import random_delay
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class WatchHandler(BaseTaskHandler):
    """观看任务处理器：

    B 站经验规则：连续观看视频累计 ≥ 300 秒（5 分钟）获得 +5 经验。
    风控要求：
      1. 心跳上报间隔必须与真实 wall-clock 时间匹配（15~25 秒一次较自然）
      2. played_time 每次增量 ≈ 真实等待时间，不能跳秒过大
      3. 总真实耗时 ≥ 300 秒
    """

    task_type: str = "watch"

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        # 默认目标时长 310 秒（比 300 多 10s 冗余），最低不低于 300
        target: int = int(config.get("duration_seconds", 310))
        if target < 300:
            target = 300
        source: str = str(config.get("source", "recommend"))

        # ① 事前查今日经验，已拿到则直接跳过
        try:
            before = await self.client.get_daily_exp_reward()
        except BiliAPIException as exc:
            logger.warning(f"watch 事前查经验状态失败: {exc}")
            before = None
        if before and before.get("watch"):
            return TaskResult(
                success=True,
                message="今日观看经验已领取，跳过",
                exp_gained=0,
                detail={"watch_exp": before.get("watch_exp", 5)},
            )

        # ② 获取目标视频
        try:
            if source == "recommend":
                videos = await self.client.get_recommend_videos(ps=1)
            else:
                videos = await self.client.get_recommend_videos(ps=1)
        except BiliAPIException as exc:
            raise TaskExecuteException(f"获取推荐视频失败: {exc}") from exc

        if not videos:
            return TaskResult(
                success=False,
                message="无可用推荐视频",
                exp_gained=0,
            )

        video = videos[0]
        bvid: str = video.get("bvid", "")
        cid: int = int(video.get("cid", 0))
        title: str = video.get("title", "")
        video_duration: int = int(video.get("duration", 0) or 0)

        if not bvid or cid == 0:
            return TaskResult(
                success=False,
                message=f"视频信息不完整: bvid={bvid} cid={cid}",
                exp_gained=0,
            )

        # 如果视频总时长 < target，就缩到视频总时长（避免报"进度超总长"）
        if video_duration and video_duration < target:
            target = video_duration
            if target < 300:
                logger.info(
                    f"watch 视频时长只有 {video_duration}s < 300s，将"
                    f"按实际播放，观看经验可能不满 +5"
                )

        # ③ 第一次上报（played_time=0，dt=0），并记录 start_ts
        start_ts = int(time.time())
        played_time = 0
        await self.client.heartbeat(
            bvid, cid, played_time,
            dt=0, start_ts=start_ts, real_played=0,
        )
        logger.debug(f"watch 首次心跳 bvid={bvid} start_ts={start_ts}")

        # ④ 每 15~25s 真实等待 + 上报一次，累计 played_time 到 target
        hb_idx = 0
        last_played = 0
        while played_time < target:
            # 真实等待 15~25 秒
            dt_seconds = await random_delay(15, 25)
            # played_time 增长 = 真实等待时间（± 小的扰动）
            import random
            inc = int(dt_seconds) + random.randint(-2, 2)
            if inc < 8:
                inc = 8
            played_time = min(target, last_played + inc)

            hb_idx += 1
            try:
                await self.client.heartbeat(
                    bvid, cid, played_time,
                    dt=int(dt_seconds),
                    start_ts=start_ts,
                    real_played=played_time,
                )
                logger.debug(
                    f"watch 心跳 #{hb_idx} bvid={bvid} "
                    f"played={played_time}s dt={int(dt_seconds)}s"
                )
            except BiliAPIException as exc:
                logger.warning(f"心跳上报失败 #{hb_idx}: {exc}")

            last_played = played_time

        # ⑤ 最后一次再上报一次收尾（played_time=target）
        try:
            await self.client.heartbeat(
                bvid, cid, target,
                dt=1, start_ts=start_ts, real_played=target,
            )
        except BiliAPIException as exc:
            logger.warning(f"watch 最终心跳失败: {exc}")

        # ⑥ 等 3~5s 然后验证经验真的给了
        await random_delay(3, 5)
        try:
            after = await self.client.get_daily_exp_reward()
        except BiliAPIException as exc:
            logger.warning(f"watch 复核经验失败: {exc}")
            after = None

        # ⑦ 0.2.0：用 refresh_exp_snapshot 拿真实经验 delta 作为主判定
        #   - delta >= 5 ⇒ 真实获得 +5（B 站可能给5或更多，但 watch 一次最多 +5）
        #   - 0 < delta < 5 ⇒ 异常情况（极少，按 delta 报）
        #   - delta = 0 ⇒ 未获得经验（可能别处已领过或风控）
        # 同时保留 after.watch 作为辅助验证
        real_elapsed = int(time.time() - start_ts)
        real_delta = await self.refresh_exp_snapshot()

        if real_delta >= 5:
            exp_gained = 5
            success = True
            status_msg = (
                f"观看 {bvid} 完成（时长 {target}s，真实约 {real_elapsed}s），"
                f"经验快照对比 +{real_delta}（真实获得）"
            )
        elif real_delta > 0:
            exp_gained = real_delta
            success = True
            status_msg = (
                f"观看 {bvid} 完成（时长 {target}s，真实约 {real_elapsed}s），"
                f"经验快照对比 +{real_delta}（少于预期，可能部分计入）"
            )
        else:
            # delta=0：可能别处已完成（B 站服务端去重），也可能是风控失败
            exp_gained = 0
            success = False
            status_msg = (
                f"观看 {bvid} 已执行（时长 {target}s，真实约 {real_elapsed}s），"
                f"但经验快照对比 delta=0（未获得经验）。"
                f"可能原因：1) 别处设备已完成观看任务（B 站服务端去重）；"
                f"2) IP/UA 风控；3) Cookie 缺 buvid3。"
                f"状态变化：before.watch="
                f"{before.get('watch') if before else None} → after.watch="
                f"{after.get('watch') if after else None}"
            )

        return TaskResult(
            success=success,
            message=status_msg,
            exp_gained=exp_gained,
            detail={
                "bvid": bvid,
                "cid": cid,
                "title": title,
                "target_duration": target,
                "video_duration": video_duration,
                "real_elapsed_s": real_elapsed,
                "heartbeat_count": hb_idx + 2,
                "before_state": before,
                "after_state": after,
                "exp_delta": real_delta,
            },
        )
