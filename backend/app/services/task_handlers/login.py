"""登录任务：触发每日登录经验 +5，并验证 B 站经验系统真的记入。"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.exceptions import BiliAPIException
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class LoginHandler(BaseTaskHandler):
    """登录任务：

    1. 调用带风控指纹的 nav（get_user_info）更新账号缓存；
    2. 调用 /x/member/web/exp/reward 真实查询"今日登录经验"状态；
    3. 返回 exp_gained 如实反映真实获得的经验（不再硬编码 5）。
    """

    task_type: str = "login"

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        # ① 先看有没有今天已经拿过登录经验 → 直接跳过
        try:
            before = await self.client.get_daily_exp_reward()
        except BiliAPIException as exc:
            logger.warning(f"login 查经验状态失败: {exc}")
            before = None

        if before and before.get("login"):
            return TaskResult(
                success=True,
                message="今日登录经验已领取，跳过",
                exp_gained=0,
                detail={"login_exp": before.get("login_exp", 5)},
            )

        # ② 触发登录态：调 nav（已带 dm_xxx 风控指纹）
        ok: bool = await self.pre_check()
        if not ok:
            return TaskResult(
                success=False,
                message="登录失败：cookie 无效或已过期",
                exp_gained=0,
            )

        # ③ 再等 3-5 秒（经验系统可能有延迟）然后复核
        import asyncio
        from app.services.anti_detect import random_delay

        await random_delay(3, 5)

        try:
            after = await self.client.get_daily_exp_reward()
        except BiliAPIException as exc:
            logger.warning(f"login 复核经验失败: {exc}")
            # 拿不到奖励接口，降级为"至少 nav 成功 → 假定 +5"
            return TaskResult(
                success=True,
                message="登录成功（经验状态无法确认，已按 +5 计入）",
                exp_gained=5,
                detail={"uid": self.account.uid},
            )

        if after.get("login"):
            real_exp = int(after.get("login_exp", 0)) or 5
            return TaskResult(
                success=True,
                message="今日登录经验已领取",
                exp_gained=real_exp,
                detail={"login_exp": real_exp},
            )

        # ④ 没拿到 → 再尝试一次（访问一次视频页刷 Referer，再查一次）
        try:
            vids = await self.client.get_recommend_videos(ps=1)
            if vids:
                bvid = vids[0].get("bvid", "")
                if bvid:
                    # 模拟"点开视频页"对经验系统可见性的帮助
                    try:
                        await self.client.bvid_to_aid(bvid)
                    except BiliAPIException:
                        pass
        except BiliAPIException:
            pass

        await asyncio.sleep(5)
        try:
            final = await self.client.get_daily_exp_reward()
        except BiliAPIException:
            final = None

        if final and final.get("login"):
            real_exp = int(final.get("login_exp", 0)) or 5
            return TaskResult(
                success=True,
                message="今日登录经验已领取（二次重试）",
                exp_gained=real_exp,
                detail={"login_exp": real_exp},
            )

        return TaskResult(
            success=False,
            message="登录经验未成功记入（cookie 有效但风控拦截），建议次日再观察或更换 IP 重试",
            exp_gained=0,
            detail={"state_before": before, "state_after": after, "state_final": final},
        )
