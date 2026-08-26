"""观看任务：通过心跳上报模拟观看视频，获取经验。"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.exceptions import BiliAPIException, TaskExecuteException
from app.services.anti_detect import random_delay
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class WatchHandler(BaseTaskHandler):
    """观看任务处理器：分 3 次上报心跳模拟真实观看。"""

    task_type: str = "watch"

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        duration: int = int(config.get("duration_seconds", 30))
        source: str = str(config.get("source", "recommend"))

        # 获取目标视频
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

        if not bvid or cid == 0:
            return TaskResult(
                success=False,
                message=f"视频信息不完整: bvid={bvid} cid={cid}",
                exp_gained=0,
            )

        # 3 次心跳上报：0、duration/2、duration
        played_times: list[int] = [0, duration // 2, duration]
        for idx, played_time in enumerate(played_times):
            try:
                await self.client.heartbeat(bvid, cid, played_time)
                logger.debug(
                    f"watch 心报 #{idx + 1} bvid={bvid} played={played_time}s"
                )
            except BiliAPIException as exc:
                logger.warning(f"心跳上报失败 #{idx + 1}: {exc}")
            # 除最后一次外，等待 5~10s
            if idx < len(played_times) - 1:
                await random_delay(5, 10)

        return TaskResult(
            success=True,
            message=f"观看 {bvid} 完成",
            exp_gained=5,
            detail={
                "bvid": bvid,
                "cid": cid,
                "title": title,
                "duration": duration,
            },
        )
