"""分享任务：调用分享接口获取经验。"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.exceptions import BiliAPIException, TaskExecuteException
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class ShareHandler(BaseTaskHandler):
    """分享任务处理器：从推荐视频取一个进行分享。"""

    task_type: str = "share"

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

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

        try:
            await self.client.share_video(bvid)
        except BiliAPIException as exc:
            logger.warning(f"分享失败 bvid={bvid}: {exc}")
            return TaskResult(
                success=False,
                message=f"分享失败: {exc}",
                exp_gained=0,
                detail={"bvid": bvid},
            )

        return TaskResult(
            success=True,
            message=f"分享 {bvid} 完成",
            exp_gained=5,
            detail={"bvid": bvid, "title": title},
        )
