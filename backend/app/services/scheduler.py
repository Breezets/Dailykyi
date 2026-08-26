"""任务调度器：基于 APScheduler AsyncIOScheduler。

负责：
- 从 TaskConfig 加载启用的任务并创建调度
- 按时触发任务，写入 TaskLog 并执行重试与失败熔断
- 暴露 next_run_time 给 dashboard
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from loguru import logger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.exceptions import TaskExecuteException
from app.models.account import Account
from app.models.task_config import TaskConfig
from app.models.task_log import TaskLog
from app.services.notify import NotifyService
from app.services.task_handlers import HANDLER_MAP, BaseTaskHandler


class TaskScheduler:
    """基于 APScheduler 的任务调度器。"""

    # 连续失败阈值：达到后自动暂停任务并通知
    FAILURE_THRESHOLD: int = 5

    # 开发中任务：强制跳过调度与执行，不写日志
    DISABLED_TASK_TYPES: set[str] = {"live_sign", "silver2coin"}

    def __init__(self) -> None:
        self.scheduler: AsyncIOScheduler = AsyncIOScheduler()
        self.jobs: dict[str, Any] = {}
        # 连续失败计数：{(uid, task_type): count}
        self._failure_counts: dict[tuple[int, str], int] = {}

    # ====== 调度加载 ======

    async def load_jobs(self, db) -> None:
        """从数据库加载所有 enabled=True 的 TaskConfig 并注册调度。"""
        # 先清空旧任务
        for job_id in list(self.jobs.keys()):
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass
        self.jobs.clear()

        result = await db.execute(
            select(TaskConfig).where(TaskConfig.enabled == True)  # noqa: E712
        )
        configs = list(result.scalars().all())

        # 跳过开发中任务，不注册调度
        configs = [c for c in configs if c.task_type not in self.DISABLED_TASK_TYPES]

        for cfg in configs:
            self._register_task(cfg)

        logger.info(f"已加载 {len(configs)} 个任务配置")

    def _register_task(self, cfg: TaskConfig) -> None:
        """为单个 TaskConfig 注册调度任务。"""
        if cfg.task_type in self.DISABLED_TASK_TYPES:
            return
        job_id = f"{cfg.account_uid}:{cfg.task_type}"

        try:
            if cfg.schedule_mode == "fixed":
                self._add_fixed_job(cfg, job_id)
            elif cfg.schedule_mode == "random":
                self._add_random_jobs(cfg, job_id)
            else:
                logger.warning(
                    f"未知 schedule_mode={cfg.schedule_mode}，跳过 {job_id}"
                )
                return
        except Exception as exc:  # noqa: BLE001
            logger.error(f"注册任务 {job_id} 失败: {exc}")

    def _add_fixed_job(self, cfg: TaskConfig, job_id: str) -> None:
        """固定时间调度：从 schedule_config 读取 hour/minute，用 CronTrigger。"""
        sc = cfg.schedule_config or {}
        hour: int = int(sc.get("hour", 8))
        minute: int = int(sc.get("minute", 0))

        trigger = CronTrigger(hour=hour, minute=minute)
        self.scheduler.add_job(
            self._job_wrapper,
            trigger=trigger,
            args=[cfg.account_uid, cfg.task_type],
            id=job_id,
            replace_existing=True,
        )
        self.jobs[job_id] = {
            "account_uid": cfg.account_uid,
            "task_type": cfg.task_type,
            "schedule_mode": "fixed",
        }
        logger.info(f"注册 fixed 任务 {job_id} at {hour:02d}:{minute:02d}")

    def _add_random_jobs(self, cfg: TaskConfig, job_id: str) -> None:
        """随机时间调度：在范围内生成多个执行点，用 DateTrigger。"""
        run_times = self.generate_random_schedule(cfg)
        if not run_times:
            logger.warning(f"随机调度未生成时间点 {job_id}")
            return

        for idx, run_time in enumerate(run_times):
            sub_id = f"{job_id}#{idx}"
            trigger = DateTrigger(run_date=run_time)
            self.scheduler.add_job(
                self._job_wrapper,
                trigger=trigger,
                args=[cfg.account_uid, cfg.task_type],
                id=sub_id,
                replace_existing=True,
            )
            self.jobs[sub_id] = {
                "account_uid": cfg.account_uid,
                "task_type": cfg.task_type,
                "schedule_mode": "random",
                "run_time": run_time.isoformat(),
            }
        logger.info(
            f"注册 random 任务 {job_id}，{len(run_times)} 个执行点"
        )

    def generate_random_schedule(self, task_config: TaskConfig) -> list[datetime]:
        """从 schedule_config 读取 time_range 与 min_interval_minutes，生成当日时间点列表。"""
        sc = task_config.schedule_config or {}
        time_range = sc.get("time_range") or {}
        start_str: str = str(time_range.get("start", "08:00"))
        end_str: str = str(time_range.get("end", "23:00"))
        min_interval_minutes: int = int(sc.get("min_interval_minutes", 30))
        count: int = int(sc.get("count", 3))

        today = datetime.now().date()
        start_dt = datetime.strptime(start_str, "%H:%M").replace(
            year=today.year, month=today.month, day=today.day
        )
        end_dt = datetime.strptime(end_str, "%H:%M").replace(
            year=today.year, month=today.month, day=today.day
        )

        if end_dt <= start_dt:
            end_dt = end_dt + timedelta(days=1)

        total_minutes = int((end_dt - start_dt).total_seconds() / 60)
        if total_minutes <= 0:
            return []

        max_attempts = 100
        attempts = 0
        points: list[datetime] = []
        while attempts < max_attempts and len(points) < count:
            attempts += 1
            offset = random.randint(0, total_minutes)
            candidate = start_dt + timedelta(minutes=offset)
            # 检查与已有点的间隔
            ok = True
            for p in points:
                if abs((candidate - p).total_seconds()) / 60 < min_interval_minutes:
                    ok = False
                    break
            if ok:
                points.append(candidate)

        points.sort()
        return points

    # ====== 任务执行 ======

    async def _job_wrapper(self, uid: int, task_type: str) -> None:
        """APScheduler 调度的入口：AsyncIOScheduler 直接 await。"""
        await self.execute_task(uid, task_type)

    async def execute_task(self, uid: int, task_type: str) -> None:
        """执行单个任务：创建独立 AsyncSession，记录 TaskLog，带重试。"""
        # 开发中任务：强制跳过，不写日志
        if task_type in self.DISABLED_TASK_TYPES:
            logger.info(f"跳过开发中任务 uid={uid} type={task_type}")
            return

        # 新建独立 session，避免与请求周期耦合
        async with AsyncSessionLocal() as db:
            # 查询账号
            acc_result = await db.execute(
                select(Account).where(Account.uid == uid)
            )
            account = acc_result.scalar_one_or_none()
            if account is None:
                logger.error(f"账号不存在 uid={uid}")
                return

            # Cookie 过期预警检查
            if account.cookie_expires_at is not None:
                remaining = (account.cookie_expires_at - datetime.now()).days
                if 0 <= remaining <= 3:
                    try:
                        notify = NotifyService(db)
                        await notify.send_cookie_warning(account, remaining)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(f"Cookie 预警发送失败: {exc}")

            # 查询任务配置
            cfg_result = await db.execute(
                select(TaskConfig).where(
                    TaskConfig.account_uid == uid,
                    TaskConfig.task_type == task_type,
                )
            )
            cfg = cfg_result.scalar_one_or_none()
            if cfg is None:
                # 手动触发时自动创建默认配置（开发中任务默认 enabled=False）
                default_enabled = task_type not in self.DISABLED_TASK_TYPES
                cfg = TaskConfig(
                    account_uid=uid,
                    task_type=task_type,
                    enabled=default_enabled,
                    config={},
                    schedule_mode="random",
                    schedule_config={},
                )
                db.add(cfg)
                await db.commit()
                await db.refresh(cfg)
                logger.info(f"自动创建任务配置 uid={uid} type={task_type}")

            handler_cls = HANDLER_MAP.get(task_type)
            if handler_cls is None:
                logger.error(f"未注册的任务类型 {task_type}")
                return

            # 创建 pending TaskLog
            log = TaskLog(
                account_uid=uid,
                task_type=task_type,
                status="pending",
                message="",
                detail={},
                exp_gained=0,
                started_at=datetime.utcnow(),
            )
            db.add(log)
            await db.commit()
            await db.refresh(log)

            # 更新为 running
            log.status = "running"
            log.message = "任务开始执行"
            await db.commit()

            # 实例化 handler
            handler: BaseTaskHandler = handler_cls(account, db)

            # init_client
            try:
                await handler.init_client()
            except Exception as exc:  # noqa: BLE001
                await self._mark_failed(
                    db, log, uid, task_type, cfg, f"init_client 失败: {exc}"
                )
                return

            # pre_check
            try:
                ok = await handler.pre_check()
            except Exception as exc:  # noqa: BLE001
                await self._mark_failed(
                    db, log, uid, task_type, cfg, f"pre_check 异常: {exc}"
                )
                return

            if not ok:
                await self._mark_failed(
                    db,
                    log,
                    uid,
                    task_type,
                    cfg,
                    "pre_check 失败：cookie 无效",
                )
                return

            # execute 带重试
            max_retries: int = max(0, int(cfg.max_retries))
            attempt: int = 0
            result = None
            last_err: str = ""
            while attempt <= max_retries:
                try:
                    result = await handler.execute(cfg.config or {})
                    break
                except TaskExecuteException as exc:
                    attempt += 1
                    last_err = str(exc)
                    logger.warning(
                        f"任务执行失败 uid={uid} type={task_type} "
                        f"attempt={attempt}/{max_retries + 1}: {exc}"
                    )
                    if attempt > max_retries:
                        break
                    # 指数退避：2^attempt 秒
                    backoff = min(2 ** attempt, 60)
                    await asyncio.sleep(backoff)
                except Exception as exc:  # noqa: BLE001
                    attempt += 1
                    last_err = f"未捕获异常: {exc}"
                    logger.exception(
                        f"任务执行未捕获异常 uid={uid} type={task_type}"
                    )
                    if attempt > max_retries:
                        break
                    backoff = min(2 ** attempt, 60)
                    await asyncio.sleep(backoff)

            if result is not None and result.success:
                # 成功
                log.status = "success" if result.exp_gained > 0 else "success"
                log.message = result.message
                log.detail = result.detail
                log.exp_gained = result.exp_gained
                log.completed_at = datetime.utcnow()
                await db.commit()
                self._failure_counts[(uid, task_type)] = 0
                logger.info(
                    f"任务成功 uid={uid} type={task_type} exp={result.exp_gained}"
                )
                try:
                    notify = NotifyService(db)
                    await notify.send_task_result(
                        account, task_type, True, result.message, result.exp_gained
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"通知发送失败: {exc}")
            elif result is not None and not result.success:
                # 业务层返回 success=False（视为 skipped）
                log.status = "skipped"
                log.message = result.message
                log.detail = result.detail
                log.exp_gained = result.exp_gained
                log.completed_at = datetime.utcnow()
                await db.commit()
                logger.info(
                    f"任务跳过 uid={uid} type={task_type}: {result.message}"
                )
            else:
                # 重试耗尽仍失败
                await self._mark_failed(
                    db, log, uid, task_type, cfg, f"重试耗尽: {last_err}"
                )
                try:
                    notify = NotifyService(db)
                    await notify.send_task_result(
                        account, task_type, False, f"重试耗尽: {last_err}", 0
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"通知发送失败: {exc}")

            # 关闭 client
            if handler.client is not None:
                try:
                    await handler.client.close()
                except Exception:  # noqa: BLE001
                    pass

    async def _mark_failed(
        self,
        db,
        log: TaskLog,
        uid: int,
        task_type: str,
        cfg: TaskConfig,
        message: str,
    ) -> None:
        """标记任务失败并触发熔断检查。"""
        log.status = "failed"
        log.message = message
        log.completed_at = datetime.utcnow()
        await db.commit()

        key = (uid, task_type)
        self._failure_counts[key] = self._failure_counts.get(key, 0) + 1
        count = self._failure_counts[key]

        logger.warning(
            f"任务失败 uid={uid} type={task_type} 连续失败={count}/{self.FAILURE_THRESHOLD} msg={message}"
        )

        if count >= self.FAILURE_THRESHOLD:
            logger.error(
                f"任务连续失败达到阈值，自动暂停 uid={uid} type={task_type}"
            )
            # 暂停任务
            cfg.enabled = False
            await db.commit()
            # 移除调度任务
            job_id = f"{uid}:{task_type}"
            for sub_id in list(self.jobs.keys()):
                if sub_id == job_id or sub_id.startswith(f"{job_id}#"):
                    try:
                        self.scheduler.remove_job(sub_id)
                    except Exception:  # noqa: BLE001
                        pass
                    self.jobs.pop(sub_id, None)
            # 发送风控告警
            try:
                # 查账号对象
                acc_result = await db.execute(
                    select(Account).where(Account.uid == uid)
                )
                acc = acc_result.scalar_one_or_none()
                if acc is not None:
                    notify = NotifyService(db)
                    await notify.send_risk_alert(acc, task_type, count)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"通知发送失败: {exc}")

    # ====== 调度器生命周期 ======

    def start(self) -> None:
        """启动调度器。"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("TaskScheduler 已启动")

    def shutdown(self) -> None:
        """关闭调度器。"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("TaskScheduler 已关闭")

    def get_upcoming(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取即将执行的任务列表。"""
        upcoming: list[dict[str, Any]] = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            if next_run is None:
                continue
            # 解析 job_id: 形如 "uid:task_type" 或 "uid:task_type#idx"
            raw_id = job.id
            base_id = raw_id.split("#", 1)[0]
            try:
                uid_str, task_type = base_id.split(":", 1)
                uid = int(uid_str)
            except ValueError:
                continue
            upcoming.append(
                {
                    "job_id": raw_id,
                    "account_uid": uid,
                    "task_type": task_type,
                    "next_run_time": next_run.isoformat() if next_run else None,
                }
            )
        upcoming.sort(key=lambda x: x["next_run_time"] or "")
        return upcoming[:limit]


# 模块级单例
scheduler: TaskScheduler = TaskScheduler()


async def init_scheduler() -> None:
    """初始化调度器：加载任务并启动。供 main.py lifespan 调用。"""
    async with AsyncSessionLocal() as db:
        await scheduler.load_jobs(db)
    scheduler.start()


async def shutdown_scheduler() -> None:
    """关闭调度器。"""
    scheduler.shutdown()
