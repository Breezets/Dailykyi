"""分享任务：调用正确参数触发 B 站经验分享计数，并真实验证 +5。"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.exceptions import BiliAPIException, TaskExecuteException
from app.services.anti_detect import random_delay
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class ShareHandler(BaseTaskHandler):
    """分享任务处理器。

    B 站 /x/member/web/exp/reward 接口只返回 bool 状态（login/watch/share），
    不返回具体经验数值。所以判断"是否触发经验"的正确逻辑是：
      before.share=False → after.share=True ⇒ 成功 +5
      before.share=False → after.share=False ⇒ 未触发，真实失败
      before.share=True  ⇒ 今日已领过，跳过
    旧的 share_exp 字段在 B 站接口里不存在，导致永远 fallback 到 `or 5` 而误报 +5。
    """

    task_type: str = "share"

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        # ① 事前查今日分享经验（B 站接口只返回 bool）
        try:
            before = await self.client.get_daily_exp_reward()
        except BiliAPIException as exc:
            logger.warning(f"share 事前查经验状态失败: {exc}")
            before = None

        if before and before.get("share"):
            return TaskResult(
                success=True,
                message="今日分享经验已领取，跳过",
                exp_gained=0,
                detail={"before_state": before},
            )

        # ② 选推荐视频
        try:
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
        title: str = video.get("title", "")
        if not bvid:
            return TaskResult(
                success=False,
                message="视频信息缺少 bvid",
                exp_gained=0,
            )

        # ③ 调用分享（_request 自动补 Origin，share_video 已带 spmid/dm_img_str 等风控参数）
        try:
            resp = await self.client.share_video(bvid)
            logger.info(f"share 调用返回 bvid={bvid} resp={resp}")
        except BiliAPIException as exc:
            logger.warning(f"分享失败 bvid={bvid}: {exc}")
            return TaskResult(
                success=False,
                message=f"分享失败: {exc}",
                exp_gained=0,
                detail={"bvid": bvid, "title": title},
            )

        # ④ 等待经验系统同步（分享延迟较大，给 6~10s）
        await random_delay(6, 10)

        try:
            after = await self.client.get_daily_exp_reward()
        except BiliAPIException as exc:
            logger.warning(f"share 复核经验失败: {exc}")
            after = None

        # ⑤ 0.2.0：用 refresh_exp_snapshot 拿真实经验 delta 作为主判定
        #   - delta >= 5 ⇒ 真实获得 +5
        #   - 0 < delta < 5 ⇒ 异常，按 delta 报
        #   - delta = 0 ⇒ 未获得经验（别处已领过 / 风控失败）
        real_delta = await self.refresh_exp_snapshot()

        if real_delta >= 5:
            return TaskResult(
                success=True,
                message=f"分享 {bvid} 完成，经验快照对比 +{real_delta}",
                exp_gained=5,
                detail={
                    "bvid": bvid,
                    "aid": resp.get("aid", 0),
                    "title": title,
                    "before_state": before,
                    "after_state": after,
                    "exp_delta": real_delta,
                },
            )
        elif real_delta > 0:
            return TaskResult(
                success=True,
                message=f"分享 {bvid} 完成，经验快照对比 +{real_delta}（少于预期）",
                exp_gained=real_delta,
                detail={
                    "bvid": bvid,
                    "aid": resp.get("aid", 0),
                    "title": title,
                    "before_state": before,
                    "after_state": after,
                    "exp_delta": real_delta,
                },
            )

        # ⑥ 真实失败：delta=0
        return TaskResult(
            success=False,
            message=(
                f"分享 API 调用成功但经验快照对比 delta=0（未获得经验）。"
                f"可能原因：1) 别处设备已完成分享任务（B 站服务端去重）；"
                f"2) 当前 IP/UA 被风控判定为非真实浏览器；"
                f"3) Cookie 缺 buvid3 或指纹不匹配。"
                f"状态变化：before.share="
                f"{before.get('share') if before else None} → after.share="
                f"{after.get('share') if after else None}"
            ),
            exp_gained=0,
            detail={
                "bvid": bvid,
                "title": title,
                "aid": resp.get("aid", 0),
                "share_resp": resp,
                "before_state": before,
                "after_state": after,
                "exp_delta": real_delta,
            },
        )
