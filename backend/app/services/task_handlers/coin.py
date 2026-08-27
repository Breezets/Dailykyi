"""投币任务：支持 fixed/smart 模式、specified/recommend 目标、本地去重。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BiliAPIException, TaskExecuteException
from app.models.coin_record import CoinRecord
from app.services.anti_detect import random_delay
from app.services.bili_api import BiliClient
from app.services.task_handlers.base import BaseTaskHandler, TaskResult


class CoinHandler(BaseTaskHandler):
    """投币任务处理器。"""

    task_type: str = "coin"

    async def _is_already_coined(self, bvid: str) -> bool:
        """查本地 CoinRecord：近 30 天是否已对该 bvid 投过币。"""
        since = datetime.utcnow() - timedelta(days=30)
        stmt = (
            select(CoinRecord)
            .where(
                CoinRecord.account_uid == self.account.uid,
                CoinRecord.bvid == bvid,
                CoinRecord.created_at >= since,
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    def _plan_coins(self, current: int, config: dict[str, Any]) -> int:
        """根据 mode 计算计划投币数。"""
        mode: str = str(config.get("mode", "fixed"))

        if mode == "fixed":
            return int(config.get("fixed_limit", 0))

        if mode == "smart":
            tiers_raw = config.get("smart_tiers") or []
            tiers = sorted(
                [dict(t) for t in tiers_raw if isinstance(t, dict)],
                key=lambda t: int(t.get("min_coins", 0)),
                reverse=True,
            )
            for tier in tiers:
                if current >= int(tier.get("min_coins", 0)):
                    return int(tier.get("daily_limit", 0))
            return 0

        return 0

    async def _build_candidates_specified(
        self, target_uids: list[int]
    ) -> list[dict[str, Any]]:
        """按指定 UID 列表收集候选视频，按发布时间倒序。"""
        candidates: list[dict[str, Any]] = []
        assert self.client is not None
        for uid in target_uids:
            try:
                videos = await self.client.get_videos_by_uid(uid, ps=5)
            except BiliAPIException as exc:
                logger.warning(f"获取 UID={uid} 视频失败: {exc}")
                continue
            # 按 created 倒序（created 为发布时间戳）
            videos_sorted = sorted(
                videos,
                key=lambda v: int(v.get("created", 0)),
                reverse=True,
            )
            candidates.extend(videos_sorted)
        return candidates

    async def _build_candidates_recommend(self, ps: int = 30) -> list[dict[str, Any]]:
        """从推荐视频流收集候选。"""
        assert self.client is not None
        try:
            return await self.client.get_recommend_videos(ps=ps)
        except BiliAPIException as exc:
            logger.warning(f"获取推荐视频失败: {exc}")
            return []

    async def _coin_one(
        self, bvid: str, title: str, owner_uid: int, owner_name: str
    ) -> bool:
        """对单个 bvid 执行投币，成功返回 True 并写入 CoinRecord。"""
        # 1. 本地查重
        if await self._is_already_coined(bvid):
            logger.debug(f"本地记录已投币 bvid={bvid}，跳过")
            return False

        # 2. 远程确认
        assert self.client is not None
        try:
            multiply = await self.client.check_coin(bvid)
        except BiliAPIException as exc:
            logger.warning(f"check_coin 失败 bvid={bvid}: {exc}")
            return False
        if multiply > 0:
            logger.debug(f"远程已投币 bvid={bvid} multiply={multiply}，跳过")
            # 同步补一条本地记录
            await self._write_coin_record(
                bvid, title, owner_uid, owner_name, coin_count=multiply
            )
            return False

        # 3. 等待 + 投币
        await random_delay(5, 15)
        try:
            await self.client.coin_video(bvid, multiply=1, select_like=0)
        except BiliAPIException as exc:
            logger.warning(f"投币失败 bvid={bvid}: {exc}")
            return False

        await self._write_coin_record(bvid, title, owner_uid, owner_name, coin_count=1)
        return True

    async def _write_coin_record(
        self,
        bvid: str,
        title: str,
        owner_uid: int,
        owner_name: str,
        coin_count: int,
    ) -> None:
        """写入 CoinRecord。"""
        record = CoinRecord(
            account_uid=self.account.uid,
            bvid=bvid,
            title=title,
            owner_uid=owner_uid,
            owner_name=owner_name,
            coin_count=coin_count,
        )
        self.db.add(record)
        await self.db.commit()

    @staticmethod
    def _video_info(v: dict[str, Any]) -> tuple[str, str, int, str]:
        """从视频 dict 提取 bvid/title/owner_uid/owner_name。"""
        bvid: str = str(v.get("bvid", "") or "")
        title: str = str(v.get("title", "") or "")
        owner_uid: int = 0
        owner_name: str = ""
        mid = v.get("mid")
        if mid is not None:
            owner_uid = int(mid)
        else:
            owner_field = v.get("owner") if isinstance(v.get("owner"), dict) else {}
            owner_uid = int(owner_field.get("mid", 0) or 0)
            owner_name = str(owner_field.get("name", "") or "")
        if not owner_name:
            owner_name = str(v.get("author", "") or "")
        return bvid, title, owner_uid, owner_name

    async def execute(self, config: dict[str, Any]) -> TaskResult:
        if self.client is None:
            await self.init_client()
        assert self.client is not None

        # 1. 当前硬币
        try:
            current = await self.client.get_coins()
        except BiliAPIException as exc:
            raise TaskExecuteException(f"获取硬币数失败: {exc}") from exc

        # 2. 计划投币数
        plan = self._plan_coins(current, config)

        # 3. reserve_coins 约束
        reserve_coins: int = int(config.get("reserve_coins", 0))
        if plan + reserve_coins > current:
            plan = max(0, current - reserve_coins)

        # 4. 计划为 0，直接跳过
        if plan <= 0:
            return TaskResult(
                success=True,
                message=f"跳过投币：硬币不足或计划为 0 (current={current}, reserve={reserve_coins})",
                exp_gained=0,
                detail={
                    "current_coins": current,
                    "reserve_coins": reserve_coins,
                    "plan": plan,
                },
            )

        # 5. 准备候选视频
        target_mode: str = str(config.get("target_mode", "recommend"))
        fallback_to_recommend: bool = bool(config.get("fallback_to_recommend", False))
        target_uids: list[int] = [
            int(uid) for uid in (config.get("target_uids") or []) if uid
        ]

        candidates: list[dict[str, Any]] = []
        if target_mode == "specified" and target_uids:
            candidates = await self._build_candidates_specified(target_uids)
        else:
            candidates = await self._build_candidates_recommend(ps=30)

        # 6. 遍历投币
        detailed: list[dict[str, Any]] = []
        actual_coined: int = 0
        remaining: int = plan

        for video in candidates:
            if remaining <= 0:
                break
            bvid, title, owner_uid, owner_name = self._video_info(video)
            if not bvid:
                continue

            done = await self._coin_one(bvid, title, owner_uid, owner_name)
            if done:
                remaining -= 1
                actual_coined += 1
                detailed.append(
                    {
                        "bvid": bvid,
                        "title": title,
                        "owner_uid": owner_uid,
                        "owner_name": owner_name,
                    }
                )

        # 6.2 fallback_to_recommend：specified 模式补足
        if (
            target_mode == "specified"
            and fallback_to_recommend
            and remaining > 0
        ):
            logger.info(
                f"切换到 recommend 模式补投，剩余计划 {remaining} 个"
            )
            recommend_candidates = await self._build_candidates_recommend(ps=30)
            # 过滤掉已投过的
            existing_bvids = {d["bvid"] for d in detailed}
            for video in recommend_candidates:
                if remaining <= 0:
                    break
                bvid, title, owner_uid, owner_name = self._video_info(video)
                if not bvid or bvid in existing_bvids:
                    continue
                done = await self._coin_one(bvid, title, owner_uid, owner_name)
                if done:
                    remaining -= 1
                    actual_coined += 1
                    detailed.append(
                        {
                            "bvid": bvid,
                            "title": title,
                            "owner_uid": owner_uid,
                            "owner_name": owner_name,
                        }
                    )

        exp_gained: int = actual_coined * 10
        # 0.2.0：用经验快照对比验证真实经验获得量
        #   - 投币期间累计获得 exp 应 ≈ actual_coined * 10
        #   - real_delta 是 nav 接口返回的真实经验变化，比推算更可靠
        #   - 容差 ±5（避免 B 站服务端经验小幅波动误判）
        real_delta = await self.refresh_exp_snapshot()
        if real_delta > 0 and abs(real_delta - exp_gained) <= 5:
            # 真实经验与推算一致，用推算值（更精确）
            final_exp = exp_gained
            delta_note = f"经验快照对比 +{real_delta}（与预期一致）"
        elif real_delta > 0:
            # 真实经验与推算不一致，按真实值报
            final_exp = real_delta
            delta_note = (
                f"经验快照对比 +{real_delta}（与预期 {exp_gained} 不符，按真实值报）"
            )
        else:
            # real_delta = 0：可能别处已完成投币任务或风控
            final_exp = 0
            delta_note = (
                f"经验快照对比 delta=0（未获得经验，可能别处已完成投币任务）"
            )

        success = final_exp > 0 or actual_coined > 0
        return TaskResult(
            success=success,
            message=(
                f"投币完成：计划 {plan}，实际 {actual_coined}。{delta_note}"
            ),
            exp_gained=final_exp,
            detail={
                "current_coins": current,
                "reserve_coins": reserve_coins,
                "plan": plan,
                "actual": actual_coined,
                "videos": detailed,
                "exp_delta": real_delta,
                "estimated_exp": exp_gained,
            },
        )
