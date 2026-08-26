"""认证路由：登录、登出、当前用户、改密、B 站扫码登录。

前缀 /api/v1/auth
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import (
    change_password,
    create_jwt_token,
    encrypt_cookie,
    get_current_user,
    is_locked,
    record_failed_attempt,
    remaining_attempts,
    reset_attempts,
    verify_credentials,
)
from app.exceptions import BiliAPIError
from app.models.account import Account
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    QrGenerateResponse,
    QrStatusResponse,
    UserInfoResponse,
)
from app.services.bili_api import BiliClient, QR_CONFIRMED, QR_EXPIRED, QR_SCANNED, QR_WAITING

router = APIRouter()


def _client_ip(request: Request) -> str:
    """提取客户端 IP（兼容反向代理场景）。"""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ====== 登录 / 登出 ======


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """用户名密码登录：失败按 IP 计数，超限锁定。"""
    ip = _client_ip(request)

    if is_locked(ip):
        logger.warning(f"IP {ip} 登录锁定中")
        raise HTTPException(status_code=423, detail="登录尝试过多，请稍后再试")

    if not await verify_credentials(db, payload.username, payload.password):
        record_failed_attempt(ip)
        remaining = remaining_attempts(ip)
        logger.warning(f"IP {ip} 登录失败，剩余 {remaining} 次")
        if remaining <= 0:
            raise HTTPException(status_code=423, detail="登录失败次数过多，已锁定 10 分钟")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"用户名或密码错误，剩余 {remaining} 次尝试",
        )

    reset_attempts(ip)
    token = create_jwt_token(payload.username)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.SESSION_MAX_AGE_SECONDS,
        path="/",
    )
    logger.info(f"用户 {payload.username} 登录成功 (ip={ip})")
    return LoginResponse(token=token, username=payload.username)


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, response: Response):
    """登出：清除 Cookie。"""
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return MessageResponse(message="已登出")


# ====== 当前用户 / 改密 ======


@router.get("/me", response_model=UserInfoResponse)
async def me(username: str = Depends(get_current_user)):
    """返回当前登录用户信息。"""
    return UserInfoResponse(username=username)


@router.post("/change-password", response_model=MessageResponse)
async def change_password_endpoint(
    payload: ChangePasswordRequest,
    username: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码：校验旧密码，存入 SystemConfig 表。"""
    if not await change_password(db, username, payload.old_password, payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )
    logger.info(f"用户 {username} 修改密码成功")
    return MessageResponse(message="密码修改成功")


# ====== B 站扫码登录 ======


@router.get("/qr", response_model=QrGenerateResponse)
async def get_qr():
    """获取 B 站扫码登录二维码。"""
    client = BiliClient()
    try:
        data = await client.generate_qrcode()
    finally:
        await client.close()
    return QrGenerateResponse(
        qrcode_key=data.get("qrcode_key", ""),
        qrcode_url=data.get("url", ""),
        expires_at=None,
    )


@router.get("/qr/status", response_model=QrStatusResponse)
async def qr_status(qrcode_key: str, db: AsyncSession = Depends(get_db)):
    """轮询扫码状态；确认登录时提取 cookie 并 upsert Account。"""
    client = BiliClient()
    try:
        result = await client.poll_qrcode(qrcode_key)
    finally:
        await client.close()

    inner_code = result.get("code")
    url = result.get("url", "")
    message = result.get("message", "")

    logger.info(f"扫码轮询结果: code={inner_code} url_len={len(url)} message={message}")

    if inner_code == QR_WAITING:
        return QrStatusResponse(status="waiting", message=message)
    if inner_code == QR_SCANNED:
        return QrStatusResponse(status="scanned", message=message)
    if inner_code == QR_EXPIRED:
        return QrStatusResponse(status="expired", message=message)
    if inner_code != QR_CONFIRMED:
        return QrStatusResponse(status="unknown", message=message)

    # confirmed：提取 cookie 与 uid
    cookie_str, uid = BiliClient.extract_cookies(url)
    if not uid or not cookie_str:
        # B 站新流程：url 只含 ticket，需请求 crossDomain URL 从 Set-Cookie 头提取
        logger.info("extract_cookies 未取到 cookie，尝试请求 crossDomain URL 换取")
        cookie_str, uid = await BiliClient.fetch_login_cookies(url)
    if not uid or not cookie_str:
        logger.error(f"解析扫码登录凭据失败: url={url}")
        raise BiliAPIError("解析登录凭据失败")

    encrypted = encrypt_cookie(cookie_str)

    # 拉取 nav 信息填充账号字段
    nav_client = BiliClient(cookies=cookie_str)
    nav: dict = {}
    try:
        nav = await nav_client.get_nav_info()
    except BiliAPIError as exc:
        logger.warning(f"拉取 nav 信息失败: {exc.message}")
    finally:
        await nav_client.close()

    # upsert Account
    account = (
        await db.execute(select(Account).where(Account.uid == uid))
    ).scalar_one_or_none()
    if account is None:
        account = Account(uid=uid)
        db.add(account)
        logger.info(f"新建 B 站账号: uid={uid}")

    account.cookie_encrypted = encrypted
    account.username = nav.get("uname") or account.username
    account.avatar_url = nav.get("face") or account.avatar_url
    level_info = nav.get("level_info") or {}

    def _safe_int(val: Any) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    account.level = _safe_int(level_info.get("current_level", 0))
    account.current_exp = _safe_int(level_info.get("current_exp", 0))
    account.next_level_exp = _safe_int(level_info.get("next_exp", 0))
    account.coins = _safe_int(nav.get("money", 0))
    account.last_login_at = datetime.now()
    account.is_active = True

    await db.commit()
    return QrStatusResponse(status="confirmed", message="登录成功", uid=uid)


@router.post("/cookie-login", response_model=QrStatusResponse)
async def cookie_login(
    payload: dict,
    db: AsyncSession = Depends(get_db),
) -> QrStatusResponse:
    """通过浏览器 Cookie 直接登录（包含 buvid3 等指纹 cookie）。"""
    cookie_str: str = (payload.get("cookie") or "").strip()
    if not cookie_str:
        raise HTTPException(status_code=400, detail="Cookie 不能为空")

    # 用 cookie 调 nav 验证身份
    client = BiliClient(cookies=cookie_str)
    try:
        nav = await client.get_nav_info()
    except BiliAPIError as exc:
        raise HTTPException(status_code=400, detail=f"Cookie 无效: {exc.message}") from exc
    finally:
        await client.close()

    uid_str = (
        client._parse_cookie("DedeUserID")
        or str(nav.get("data", {}).get("mid", ""))
    )
    if not uid_str or not uid_str.isdigit():
        raise HTTPException(status_code=400, detail="无法从 Cookie 解析 UID")
    uid = int(uid_str)

    encrypted = encrypt_cookie(cookie_str)

    # upsert Account
    account = (
        await db.execute(select(Account).where(Account.uid == uid))
    ).scalar_one_or_none()
    if account is None:
        account = Account(uid=uid)
        db.add(account)
        logger.info(f"Cookie 登录新建 B 站账号: uid={uid}")
    else:
        logger.info(f"Cookie 登录更新 B 站账号: uid={uid}")

    account.cookie_encrypted = encrypted
    account.username = nav.get("uname") or account.username
    account.avatar_url = nav.get("face") or account.avatar_url
    level_info = nav.get("level_info") or {}

    def _safe_int(val: Any) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    account.level = _safe_int(level_info.get("current_level", 0))
    account.current_exp = _safe_int(level_info.get("current_exp", 0))
    account.next_level_exp = _safe_int(level_info.get("next_exp", 0))
    account.coins = _safe_int(nav.get("money", 0))
    account.last_login_at = datetime.now()
    account.is_active = True

    await db.commit()
    return QrStatusResponse(status="confirmed", message="Cookie 登录成功", uid=uid)
