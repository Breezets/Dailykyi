"""认证依赖：JWT token、密码校验、登录限制、cookie 加密。"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.system_config import SystemConfig

# ====== 密码哈希（pbkdf2_hmac，无 bcrypt 72 字节限制） ======

_PBKDF2_ITERATIONS = 100_000
_PBKDF2_ALGO = "pbkdf2_sha256"


def hash_password(plain: str) -> str:
    """使用 pbkdf2_hmac 哈希密码，格式：pbkdf2_sha256$<iter>$<salt_b64>$<hash_b64>。"""
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(plain: str, hashed: str) -> bool:
    """校验密码与哈希是否匹配。"""
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != _PBKDF2_ALGO:
            return False
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2])
        expected = base64.b64decode(parts[3])
        digest = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(digest, expected)
    except Exception:
        return False


# ====== 密码存储（优先 SystemConfig 表，回退默认凭据） ======


async def _get_stored_password(db: AsyncSession, username: str) -> str | None:
    """从 SystemConfig 表读取已修改的密码哈希。"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "admin_password")
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        return None
    val = cfg.value
    if isinstance(val, dict):
        return val.get(username)
    return None


async def _set_stored_password(db: AsyncSession, username: str, hashed: str) -> None:
    """将新密码哈希写入 SystemConfig 表。"""
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.key == "admin_password")
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        cfg = SystemConfig(key="admin_password", value={username: hashed})
        db.add(cfg)
    else:
        val = cfg.value if isinstance(cfg.value, dict) else {}
        val[username] = hashed
        cfg.value = val
    await db.commit()


def is_default_password(username: str, password: str) -> bool:
    return username == settings.DEFAULT_USERNAME and password == settings.DEFAULT_PASSWORD


async def verify_credentials(db: AsyncSession, username: str, password: str) -> bool:
    stored = await _get_stored_password(db, username)
    if stored:
        return verify_password(password, stored)
    return is_default_password(username, password)


async def change_password(db: AsyncSession, username: str, old_password: str, new_password: str) -> bool:
    if not await verify_credentials(db, username, old_password):
        return False
    await _set_stored_password(db, username, hash_password(new_password))
    return True


# ====== JWT Token ======


def create_jwt_token(username: str) -> str:
    """生成 JWT token。"""
    expire = datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_MAX_AGE_SECONDS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_jwt_token(token: str) -> str | None:
    """验证 JWT 并返回用户名；失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        return None


# ====== 登录尝试限制（内存，按 client IP） ======


@dataclass
class AttemptInfo:
    count: int = 0
    locked_until: float = 0.0


_login_attempts: dict[str, AttemptInfo] = {}


def is_locked(ip: str) -> bool:
    info = _login_attempts.get(ip)
    if info is None:
        return False
    if info.locked_until and time.time() < info.locked_until:
        return True
    return False


def remaining_attempts(ip: str) -> int:
    info = _login_attempts.get(ip)
    if info is None or (info.locked_until and time.time() >= info.locked_until):
        return settings.MAX_LOGIN_ATTEMPTS
    return max(0, settings.MAX_LOGIN_ATTEMPTS - info.count)


def record_failed_attempt(ip: str) -> None:
    info = _login_attempts.get(ip)
    now = time.time()
    if info is None:
        info = AttemptInfo()
        _login_attempts[ip] = info
    if info.locked_until and now >= info.locked_until:
        info.count = 0
        info.locked_until = 0.0
    info.count += 1
    if info.count >= settings.MAX_LOGIN_ATTEMPTS:
        info.locked_until = now + settings.LOGIN_LOCKOUT_MINUTES * 60


def reset_attempts(ip: str) -> None:
    _login_attempts.pop(ip, None)


# ====== Cookie 加密（Fernet 对称加密） ======


def _fernet_key() -> bytes:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_fernet_key())


def encrypt_cookie(plain: str) -> str:
    if not plain:
        return ""
    return _fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_cookie(cipher: str) -> str:
    if not cipher:
        return ""
    try:
        return _fernet.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
    except Exception:
        return ""


# ====== FastAPI 依赖 ======


async def get_current_user(request: Request) -> str:
    """从 Authorization header 或 Cookie 提取 JWT，返回当前登录用户名。"""
    # 优先检查 Authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        username = verify_jwt_token(token)
        if username:
            return username

    # 回退到 Cookie
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        username = verify_jwt_token(token)
        if username:
            return username

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录或会话失效"
    )
