"""任务处理器集合：导出所有 Handler 与 HANDLER_MAP。"""

from app.services.task_handlers.base import BaseTaskHandler, TaskResult
from app.services.task_handlers.coin import CoinHandler
from app.services.task_handlers.live_sign import LiveSignHandler
from app.services.task_handlers.login import LoginHandler
from app.services.task_handlers.share import ShareHandler
from app.services.task_handlers.silver2coin import Silver2CoinHandler
from app.services.task_handlers.watch import WatchHandler

HANDLER_MAP: dict[str, type[BaseTaskHandler]] = {
    "login": LoginHandler,
    "watch": WatchHandler,
    "coin": CoinHandler,
    "share": ShareHandler,
    "live_sign": LiveSignHandler,
    "silver2coin": Silver2CoinHandler,
}

__all__ = [
    "BaseTaskHandler",
    "TaskResult",
    "LoginHandler",
    "WatchHandler",
    "CoinHandler",
    "ShareHandler",
    "LiveSignHandler",
    "Silver2CoinHandler",
    "HANDLER_MAP",
]
