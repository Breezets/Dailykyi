"""B 站 Wbi 签名算法。

用于对需要 Wbi 签名的接口（如 x/space/wbi/arc/search）进行参数签名。
算法核心：从 nav 接口获取 img_key + sub_key，通过混淆表生成 mixin_key，
对参数排序、URL 编码后拼接 mixin_key 做 MD5 得到 w_rid。
"""

from __future__ import annotations

import hashlib
import time
from typing import Any
from urllib.parse import quote
from urllib.parse import urlparse

import httpx
from loguru import logger

# Wbi 签名混淆表（官方固定值）
MIXIN_KEY_ENC_TAB: list[int] = [
    46, 47, 18, 2, 8, 18, 40, 30, 43, 6, 44, 43, 46, 43, 4, 44,
    43, 42, 43, 8, 43, 42, 43, 5, 43, 26, 43, 43, 43, 43, 43, 43,
]

NAV_URL = "https://api.bilibili.com/x/web-interface/nav"

# 模块级缓存
_cached_keys: tuple[str, str] | None = None
_cached_at: float = 0.0
_CACHE_TTL: int = 3600  # 1 小时


def _get_mixin_key(raw_key: str) -> str:
    """通过混淆表从 raw_key（img_key + sub_key）提取 32 字节 mixin_key。"""
    return "".join(raw_key[idx] for idx in MIXIN_KEY_ENC_TAB)[:32]


def _encode_params(params: dict[str, Any]) -> str:
    """按 key 排序、URL 编码 value，拼接成 key=value&key=value。"""
    return "&".join(
        f"{k}={quote(str(v), safe='')}"
        for k, v in sorted(params.items())
    )


async def get_wbi_keys() -> tuple[str, str]:
    """异步调用 nav 接口，提取 img_key 和 sub_key（文件名部分）。"""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(NAV_URL)
        resp.raise_for_status()
        data = resp.json()["data"]
        img_url: str = data["wbi_img"]["img_url"]
        sub_url: str = data["wbi_img"]["sub_url"]

    img_key = _extract_key_from_url(img_url)
    sub_key = _extract_key_from_url(sub_url)
    logger.debug(f"Wbi keys: img_key={img_key[:8]}... sub_key={sub_key[:8]}...")
    return img_key, sub_key


def _extract_key_from_url(url: str) -> str:
    """从 URL 中提取文件名（去掉路径和扩展名）。"""
    path = urlparse(url).path
    filename = path.rsplit("/", 1)[-1]
    return filename.rsplit(".", 1)[0]


def get_wbi_sign(params: dict[str, Any], img_key: str, sub_key: str) -> dict[str, Any]:
    """对 params 进行 Wbi 签名。

    1. mixin_key = _get_mixin_key(img_key + sub_key)
    2. 添加 wts=当前时间戳
    3. 按 key 排序 + URL 编码 value，拼接成 query string
    4. query + mixin_key 做 MD5 得到 w_rid
    5. 返回原 params 加上 {wts, w_rid}
    """
    mixin_key = _get_mixin_key(img_key + sub_key)
    signed_params: dict[str, Any] = {**params, "wts": int(time.time())}
    query = _encode_params(signed_params)
    w_rid = hashlib.md5(f"{query}{mixin_key}".encode("utf-8")).hexdigest()
    signed_params["w_rid"] = w_rid
    return signed_params


async def refresh_wbi_keys() -> tuple[str, str]:
    """带 1 小时缓存的异步获取 Wbi keys。"""
    global _cached_keys, _cached_at
    now = time.time()
    if _cached_keys is not None and now - _cached_at < _CACHE_TTL:
        return _cached_keys
    try:
        _cached_keys = await get_wbi_keys()
        _cached_at = now
    except Exception as exc:
        logger.warning(f"刷新 Wbi keys 失败: {exc}")
        if _cached_keys is not None:
            return _cached_keys
        raise
    return _cached_keys
