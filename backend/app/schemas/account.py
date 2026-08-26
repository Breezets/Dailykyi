"""账号 schema：响应模型（不暴露 cookie_encrypted）。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountOut(BaseModel):
    """B 站账号对外响应。"""

    id: int
    uid: int
    username: str | None = None
    avatar_url: str | None = None
    level: int = 0
    current_exp: int = 0
    next_level_exp: int = 0
    coins: int = 0
    is_active: bool = True
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccountBrief(BaseModel):
    """账号简要信息（列表用）。"""

    id: int
    uid: int
    username: str | None = None
    avatar_url: str | None = None
    level: int = 0
    coins: int = 0
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)
