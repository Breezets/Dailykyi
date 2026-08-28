"""任务相关 Pydantic schema。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskConfigSchema(BaseModel):
    """TaskConfig 序列化。"""

    id: int
    account_uid: int
    task_type: str
    enabled: bool
    config: dict[str, Any] = Field(default_factory=dict)
    schedule_mode: str = "random"
    schedule_config: dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 3
    cooldown_minutes: int = 10
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskConfigUpdate(BaseModel):
    """更新 TaskConfig 的请求体。"""

    enabled: bool | None = None
    schedule_mode: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    schedule_config: dict[str, Any] = Field(default_factory=dict)


class TaskLogSchema(BaseModel):
    """TaskLog 序列化。"""

    id: int
    account_uid: int
    task_type: str
    status: str
    message: str | None = None
    detail: dict[str, Any] | None = None
    exp_gained: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskTriggerResponse(BaseModel):
    """手动触发任务的响应。"""

    task_log_id: int
    status: str


class DashboardAccount(BaseModel):
    """仪表盘账号信息。"""

    uid: int
    username: str | None = None
    avatar_url: str | None = None
    level: int = 0
    current_exp: int = 0
    next_level_exp: int = 0
    coins: int = 0
    today_exp_gained: int = 0
    # 0.2.1 新增：今日经验拆分（平台获得/其他设备获得/合计）
    today_exp_split: dict[str, Any] | None = None
    lv6_estimate: dict[str, Any] | None = None


class DashboardStats(BaseModel):
    """当日任务统计。"""

    total_tasks: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0


class DashboardLog(BaseModel):
    """仪表盘日志条目。"""

    id: int
    account_uid: int
    account_name: str | None = None
    task_type: str
    status: str
    message: str | None = None
    exp_gained: int = 0
    created_at: datetime


class DashboardUpcoming(BaseModel):
    """即将执行的任务。"""

    job_id: str
    account_uid: int
    task_type: str
    next_run_time: str | None = None


class DashboardResponse(BaseModel):
    """仪表盘聚合响应。"""

    accounts: list[DashboardAccount]
    today_stats: DashboardStats
    recent_logs: list[DashboardLog]
    upcoming: list[DashboardUpcoming]
