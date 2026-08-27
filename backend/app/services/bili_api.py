"""B 站 HTTP API 客户端：自动 Wbi 签名 + Cookie 注入 + CSRF 处理。

保留扫码登录方法供 auth.py 使用。
"""

from __future__ import annotations

import time
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
from loguru import logger

from app.config import settings
from app.exceptions import BiliAPIException
from app.services.bili_wbi import get_wbi_sign, refresh_wbi_keys

# 扫码状态码（供 auth.py 导入）
QR_WAITING = 86101
QR_SCANNED = 86090
QR_CONFIRMED = 0
QR_EXPIRED = 86038


class BiliClient:
    """B 站 API 客户端：基于 cookie 的会话封装，自动处理 Wbi 签名与 CSRF。"""

    API_BASE = "https://api.bilibili.com"
    PASSPORT_BASE = "https://passport.bilibili.com"

    def __init__(self, cookies: str | None = None) -> None:
        self.cookies: str = cookies or ""
        self._client: httpx.AsyncClient | None = None

        # 从 cookie 解析关键字段
        self.sessdata: str = self._parse_cookie("SESSDATA")
        self.csrf: str = self._parse_cookie("bili_jct")
        uid_str: str = self._parse_cookie("DedeUserID")
        self.uid: int = int(uid_str) if uid_str and uid_str.isdigit() else 0

    # ====== 内部工具 ======

    def _parse_cookie(self, name: str) -> str:
        """从 cookie 字符串中解析单个值。"""
        if not self.cookies:
            return ""
        for part in self.cookies.split(";"):
            k, _, v = part.strip().partition("=")
            if k == name:
                return v
        return ""

    @staticmethod
    def _gen_buvid3() -> str:
        """生成随机 buvid3（备用，B站可能不接受）。"""
        import uuid
        return str(uuid.uuid4()).upper() + "infoc"

    async def _fetch_buvid3(self) -> str:
        """从 B站 获取真实 buvid3（访问首页触发 Set-Cookie）。"""
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": settings.BILI_USER_AGENT},
                timeout=10,
            ) as c:
                resp = await c.get("https://www.bilibili.com")
                # 从 Set-Cookie 提取 buvid3
                for cookie in resp.headers.get_list("set-cookie"):
                    if cookie.startswith("buvid3="):
                        val = cookie.split(";")[0].split("=", 1)[1]
                        if val:
                            logger.info(f"获取 buvid3 成功: {val[:20]}...")
                            return val
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"获取 buvid3 失败: {exc}")
        return ""

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            # 确保 buvid3 存在（B站 POST API 风控需要）
            if self.cookies and "buvid3" not in self.cookies:
                buvid3 = await self._fetch_buvid3()
                if buvid3:
                    self.cookies += f"; buvid3={buvid3}"
            headers: dict[str, str] = {
                "User-Agent": settings.BILI_USER_AGENT,
                "Referer": "https://www.bilibili.com",
            }
            if self.cookies:
                headers["Cookie"] = self.cookies
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=settings.BILI_API_TIMEOUT,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        need_wbi: bool = False,
        need_csrf: bool = False,
        check_code: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """通用请求：自动 Wbi 签名、CSRF 注入、错误处理。

        check_code=False 时跳过业务码校验（扫码轮询需要，因其用非 0 码表达业务状态）。
        extra_headers 可传视频专属 Referer 等。
        """
        client = await self._get_client()
        url = path if path.startswith("http") else f"{self.API_BASE}/{path}"

        # Wbi 签名
        if need_wbi and params is not None:
            try:
                img_key, sub_key = await refresh_wbi_keys()
                params = get_wbi_sign(params, img_key, sub_key)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Wbi 签名失败，降级为无签名: {exc}")

        # CSRF 注入
        if need_csrf:
            data = dict(data or {})
            data.setdefault("csrf", self.csrf)

        # B 站 POST 接口必查 Origin 头（缺了会返回 code=0 但不记录业务行为，是 share/coin 类接口"看着成功但没经验"的根因）
        if method.upper() == "POST":
            extra_headers = dict(extra_headers or {})
            extra_headers.setdefault("Origin", "https://www.bilibili.com")

        try:
            resp = await client.request(method, url, params=params, data=data, headers=extra_headers)
        except httpx.HTTPError as exc:
            logger.warning(f"B 站请求失败 {method} {url}: {exc}")
            raise BiliAPIException(f"请求失败: {exc}") from exc

        # 调试日志：POST 请求记录完整响应
        if method == "POST" and resp.status_code != 200:
            logger.info(f"B站 POST {path} resp_code={resp.status_code} body={resp.text[:500]}")

        if resp.status_code != 200:
            raise BiliAPIException(
                f"HTTP {resp.status_code}: {path}", code=resp.status_code
            )

        try:
            payload = resp.json()
        except ValueError as exc:
            raise BiliAPIException(f"响应解析失败: {exc}") from exc

        if check_code and payload.get("code") not in (0, None):
            raise BiliAPIException(
                f"B 站错误: code={payload.get('code')} msg={payload.get('message')}",
                code=int(payload.get("code", 502)),
            )
        return payload

    # ====== 扫码登录（供 auth.py 调用） ======

    async def generate_qrcode(self) -> dict[str, Any]:
        """获取登录二维码。"""
        url = f"{self.PASSPORT_BASE}/x/passport-login/web/qrcode/generate"
        payload = await self._request("GET", url)
        return payload["data"]

    async def poll_qrcode(self, qrcode_key: str) -> dict[str, Any]:
        """轮询扫码状态。跳过业务码校验：86101/86090/86038 是正常业务状态而非错误。"""
        url = f"{self.PASSPORT_BASE}/x/passport-login/web/qrcode/poll"
        payload = await self._request(
            "GET", url, params={"qrcode_key": qrcode_key}, check_code=False
        )
        # 兼容：业务码可能在顶层或 data 内
        data = payload.get("data") or {}

        # 确认登录但 url 为空时，从 httpx cookie jar 兜底构造 crossDomain URL
        if data.get("code") == QR_CONFIRMED and not data.get("url"):
            client = await self._get_client()
            keys = ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid")
            pairs = [f"{k}={client.cookies.get(k)}" for k in keys if client.cookies.get(k)]
            if pairs:
                built = "https://passport.bilibili.com/crossDomain?" + "&".join(pairs)
                logger.info(f"从 cookie jar 构造 crossDomain url: {built[:80]}...")
                data = {**data, "url": built}

        return data if data else payload

    @staticmethod
    def extract_cookies(url: str) -> tuple[str, int | None]:
        """从确认登录后的 crossDomain URL 解析 cookie 字符串与 uid。"""
        if not url:
            logger.warning("extract_cookies: url 为空")
            return "", None
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        cookie_keys = ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid")
        cookies: dict[str, str] = {}
        for k in cookie_keys:
            vals = params.get(k)
            if vals:
                cookies[k] = vals[0]
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        dede = cookies.get("DedeUserID")
        uid = int(dede) if dede and dede.isdigit() else None
        if not uid or not cookies.get("SESSDATA"):
            logger.warning(f"extract_cookies 解析不完整: url={url} keys={list(cookies.keys())}")
        return cookie_str, uid

    @staticmethod
    async def fetch_login_cookies(cross_domain_url: str) -> tuple[str, int | None]:
        """B 站新流程：crossDomain URL 只含 ticket，需请求该 URL 从 Set-Cookie 头提取 cookie。"""
        if not cross_domain_url:
            return "", None
        cookie_keys = ("SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid")
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": settings.BILI_USER_AGENT,
                    "Referer": "https://www.bilibili.com",
                },
                timeout=settings.BILI_API_TIMEOUT,
                follow_redirects=False,
            ) as client:
                resp = await client.get(cross_domain_url)
                cookies: dict[str, str] = {}
                for name in cookie_keys:
                    val = resp.cookies.get(name)
                    if val:
                        cookies[name] = val
                # 若 302 未带 cookie，尝试跟随一次重定向
                if not cookies.get("SESSDATA") and resp.status_code in (301, 302, 303, 307, 308):
                    loc = resp.headers.get("location", "")
                    if loc:
                        async with httpx.AsyncClient(
                            headers={
                                "User-Agent": settings.BILI_USER_AGENT,
                                "Referer": "https://www.bilibili.com",
                            },
                            timeout=settings.BILI_API_TIMEOUT,
                            follow_redirects=False,
                        ) as client2:
                            resp2 = await client2.get(loc)
                            for name in cookie_keys:
                                val = resp2.cookies.get(name)
                                if val:
                                    cookies[name] = val
                cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
                dede = cookies.get("DedeUserID")
                uid = int(dede) if dede and dede.isdigit() else None
                logger.info(f"fetch_login_cookies: status={resp.status_code} keys={list(cookies.keys())} uid={uid}")
                return cookie_str, uid
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"fetch_login_cookies 失败: {exc}")
            return "", None

    # ====== 用户信息 ======

    async def get_user_info(self) -> dict[str, Any]:
        """GET x/web-interface/nav，携带浏览器风控指纹参数避免被判定爬虫。"""
        # 伪造浏览器 canvas / webgl 指纹（nav 风控需要，否则 isLogin 时真而不计经验）
        dm_img_list = "[]"
        # base64 伪造一段 1x1 像素 jpeg（dm_img_str / dm_cover_img_str 格式要求）
        dm_img_str = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
        dm_cover_img_str = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAASsB0HwAAAAASUVORK5CYII="
        )
        params: dict[str, Any] = {
            "dm_img_list": dm_img_list,
            "dm_img_str": dm_img_str,
            "dm_cover_img_str": dm_cover_img_str,
        }
        payload = await self._request("GET", "x/web-interface/nav", params=params)
        return payload["data"]

    async def get_nav_info(self) -> dict[str, Any]:
        """get_user_info 别名（兼容 auth.py）。"""
        return await self.get_user_info()

    async def get_coins(self) -> int:
        """从 nav 响应 data.money 提取当前硬币数。"""
        data = await self.get_user_info()
        return int(data.get("money", 0))

    # ====== 经验奖励状态 ======

    async def get_daily_exp_reward(self) -> dict[str, Any]:
        """查当日基础经验奖励是否已领取（login/watch/share 为 bool；coins 为今日投币已得经验）。

        B 站 /x/member/web/exp/reward 接口真实返回字段（按官方 bilibili-api-collect 文档）：
          login: bool    今日是否已登录（完成奖励 5 经验）
          watch: bool    今日是否已观看（完成奖励 5 经验）
          coins: num     今日投币已得经验（上限 50）
          share: bool    今日是否已分享（完成奖励 5 经验）
          email/tel/safe_question/identify_card: bool（账号安全一次性任务）
        注意：本接口不返回 *_exp 数值字段，任何对 login_exp / share_exp 等的读取都是错的。
        """
        payload = await self._request(
            "GET", "x/member/web/exp/reward",
            extra_headers={"Referer": "https://www.bilibili.com/"},
        )
        data = payload.get("data", {}) or {}
        return {
            "login": bool(data.get("login", False)),
            "watch": bool(data.get("watch", False)),
            "share": bool(data.get("share", False)),
            "coins": int(data.get("coins", 0) or 0),
            "raw": data,
        }

    # ====== 视频相关 ======

    async def get_videos_by_uid(
        self, uid: int, pn: int = 1, ps: int = 30
    ) -> list[dict[str, Any]]:
        """GET x/space/wbi/arc/search（需要 Wbi 签名）。"""
        params: dict[str, Any] = {
            "mid": uid,
            "pn": pn,
            "ps": ps,
            "order": "pubdate",
        }
        payload = await self._request(
            "GET", "x/space/wbi/arc/search",
            params=params, need_wbi=True,
        )
        vlist = payload.get("data", {}).get("list", {}).get("vlist", [])
        return list(vlist) if vlist else []

    async def get_recommend_videos(self, ps: int = 30) -> list[dict[str, Any]]:
        """GET x/web-interface/index/top/feed/rcmd（推荐视频流）。"""
        params: dict[str, Any] = {
            "ps": ps,
            "fresh_type": 4,
            "fresh_idx": int(time.time()),
            "fresh_idx_1": int(time.time()),
        }
        payload = await self._request(
            "GET", "x/web-interface/index/top/feed/rcmd",
            params=params,
        )
        items = payload.get("data", {}).get("item", [])
        return list(items) if items else []

    async def check_coin(self, bvid: str) -> int:
        """GET x/web-interface/archive/coins，返回已投币数 (0/1/2)。"""
        params: dict[str, Any] = {"bvid": bvid}
        payload = await self._request(
            "GET", "x/web-interface/archive/coins",
            params=params,
            extra_headers={"Referer": f"https://www.bilibili.com/video/{bvid}"},
        )
        multiply = payload.get("data", {}).get("multiply", 0)
        return int(multiply)

    async def coin_video(
        self, bvid: str, multiply: int = 1, select_like: int = 0
    ) -> dict[str, Any]:
        """POST x/web-interface/coin/add（需要 CSRF + 视频 Referer）。"""
        data: dict[str, Any] = {
            "bvid": bvid,
            "multiply": multiply,
            "select_like": select_like,
        }
        payload = await self._request(
            "POST", "x/web-interface/coin/add",
            data=data, need_csrf=True,
            extra_headers={"Referer": f"https://www.bilibili.com/video/{bvid}"},
        )
        return payload.get("data", {})

    async def heartbeat(
        self,
        bvid: str,
        cid: int,
        played_time: int,
        *,
        dt: int = 0,
        start_ts: int = 0,
        real_played: int = 0,
    ) -> dict[str, Any]:
        """POST x/click-interface/web/heartbeat（真实播放进度上报）。

        为通过 B 站风控判定：
          - played_time 与 dt 必须匹配（两次上报的 dt ≈ played_time 差值）
          - 需带上 play_type=1 / type=3（播放页常规上报）
          - start_ts 是视频开始播放的 unix 时间戳
          - Referer 必须为该视频页
        """
        import secrets

        data: dict[str, Any] = {
            "type": 3,                    # 3 = 播放页 heartbeat
            "sub_type": 0,
            "play_type": 1,               # 1 = 普通播放
            "bvid": bvid,
            "cid": cid,
            "played_time": played_time,
            "progress": real_played if real_played > 0 else played_time,
            "dt": max(int(dt) * 1000, 0), # 与上次上报的真实间隔（毫秒）
            "start_ts": start_ts if start_ts > 0 else int(time.time()),
            "sid": int(time.time() * 1000) & 0xFFFFFFFF,
            "spmid": "333.999",
            "csrf": self.csrf,
        }
        # 加一个 8 位随机串（防缓存/去重）
        data["visit_id"] = secrets.token_hex(4)
        payload = await self._request(
            "POST", "x/click-interface/web/heartbeat",
            data=data,
            extra_headers={"Referer": f"https://www.bilibili.com/video/{bvid}"},
        )
        return payload.get("data", {})

    async def bvid_to_aid(self, bvid: str) -> int:
        """根据 bvid 解析 aid（分享接口底层靠 aid）。"""
        params = {"bvid": bvid}
        payload = await self._request(
            "GET", "x/web-interface/view", params=params,
            extra_headers={"Referer": f"https://www.bilibili.com/video/{bvid}"},
        )
        return int(payload.get("data", {}).get("aid", 0))

    async def share_video(self, bvid: str) -> dict[str, Any]:
        """POST x/web-interface/share/add。

        B 站 Web 端分享接口（鉴权 Cookie + buvid3）。参考可跑通的开源脚本与官方文档：
          - 必带：aid / bvid / csrf / share_channel
          - 不带：source=pc_web（错值，会被判异常；旧版风控字段已废弃，省略即可）
          - 风控指纹：spmid（视频页固定 spmid 333.1007.0.1）、dm_img_str/dm_cover_img_str（与 nav 一致）
          - 请求头：Origin（_request 已自动补）、Referer=视频页
        """
        aid: int = await self.bvid_to_aid(bvid)
        data: dict[str, Any] = {
            "bvid": bvid,
            "aid": aid,
            "share_channel": "copy",
            "spmid": "333.1007.0.1",
            "from_spmid": "333.337.0.0",
            "dm_img_list": "[]",
            # 1x1 透明 png 的 base64，模拟浏览器 canvas 指纹（与 nav 一致）
            "dm_img_str": (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
            ),
            "dm_cover_img_str": (
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNgYAAAAAMAASsB0HwAAAAASUVORK5CYII="
            ),
            "csrf": self.csrf,
        }
        payload = await self._request(
            "POST", "x/web-interface/share/add",
            data=data, need_csrf=True,
            extra_headers={"Referer": f"https://www.bilibili.com/video/{bvid}"},
        )
        return {"aid": aid, **(payload.get("data", {}) or {})}

    # ====== 签到 / 兑换 ======

    async def live_sign(self) -> dict[str, Any]:
        """GET x/live/web-interface/sign/v1/signIn。"""
        payload = await self._request("GET", "x/live/web-interface/sign/v1/signIn")
        return payload.get("data", {})

    async def silver2coin(self, csrf: str | None = None) -> dict[str, Any]:
        """POST x/web-interface/coin/silver2coin（需要 CSRF）。"""
        token = csrf or self.csrf
        data: dict[str, Any] = {"csrf": token}
        payload = await self._request(
            "POST", "x/web-interface/coin/silver2coin",
            data=data,
        )
        return payload.get("data", {})


async def new_bili_client(cookies: str | None = None) -> BiliClient:
    """工厂：根据 cookies 创建客户端。"""
    return BiliClient(cookies=cookies)
