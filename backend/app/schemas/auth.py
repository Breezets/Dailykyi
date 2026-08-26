"""认证相关 schema。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str = Field(..., description="JWT token")
    username: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=6, max_length=128)


class QrGenerateResponse(BaseModel):
    qrcode_key: str
    qrcode_url: str
    expires_at: int | None = Field(None, description="二维码过期 Unix 时间戳")


class QrStatusResponse(BaseModel):
    status: str = Field(..., description="waiting/scanned/confirmed/expired")
    message: str = ""
    uid: int | None = Field(None, description="仅 confirmed 时返回 B 站 UID")


class UserInfoResponse(BaseModel):
    username: str


class MessageResponse(BaseModel):
    message: str
