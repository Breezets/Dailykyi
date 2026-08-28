"""应用配置：基于 Pydantic Settings，支持 .env 文件覆盖。"""

import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"


def _default_secret_key() -> str:
    """每次进程启动随机生成；生产环境务必通过 .env 固定。"""
    return secrets.token_urlsafe(32)


class Settings(BaseSettings):
    """全局配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DAILYKYI_",
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "Dailykyi"
    APP_VERSION: str = "0.2.1"
    DEBUG: bool = False

    # 安全
    SECRET_KEY: str = _default_secret_key()

    # 数据库（async aiosqlite）
    DATABASE_URL: str = "sqlite+aiosqlite:///data/dailykyi.db"

    # 默认管理员（登录后端用）
    DEFAULT_USERNAME: str = "2233"
    DEFAULT_PASSWORD: str = "tv23333"

    # 登录限制
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 10

    # Session Cookie
    SESSION_COOKIE_NAME: str = "dailykyi_session"
    SESSION_MAX_AGE_SECONDS: int = 86400  # 1 天

    # B 站 API
    BILI_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    BILI_API_TIMEOUT: int = 10

    # 日志
    LOG_LEVEL: str = "INFO"


settings = Settings()
