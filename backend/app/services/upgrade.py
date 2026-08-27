"""版本升级检测与一键升级服务（0.2.0）。

- check_update: 调用 GitHub Releases API 与当前版本比较
- run_update: 执行 scripts/update.sh（git pull + 前端构建 + 重建容器）
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from app.config import BASE_DIR, LOG_DIR, settings

# 开源仓库（发布新版本时保持与 README 一致）
GITHUB_REPO = "breezets/Dailykyi"
RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TAGS_API = f"https://api.github.com/repos/{GITHUB_REPO}/tags"

UPDATE_SCRIPT = BASE_DIR.parent / "scripts" / "update.sh"
UPGRADE_LOG = LOG_DIR / "upgrade.log"


def parse_version(ver: str) -> tuple[int, ...]:
    """将 'v0.2.0' / '0.10.1' 等解析为可比较的元组。"""
    clean = ver.strip().lower().lstrip("v")
    parts: list[int] = []
    for seg in clean.split("."):
        num = ""
        for ch in seg:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts)


async def check_update() -> dict[str, Any]:
    """查询 GitHub 最新版本（优先 releases/latest，无 release 时回退 tags），与当前版本比较。

    网络失败时降级返回 has_update=False + error 信息，不阻塞主流程。
    """
    current = settings.APP_VERSION
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(
                RELEASE_API,
                headers={"Accept": "application/vnd.github+json"},
            )
        if resp.status_code == 200:
            data = resp.json()
            latest_tag = str(data.get("tag_name", "")).lstrip("v")
            return {
                "has_update": bool(parse_version(latest_tag)) and parse_version(latest_tag) > parse_version(current),
                "current": current,
                "latest": latest_tag or None,
                "release_url": data.get("html_url"),
                "notes": (data.get("body") or "")[:2000],
                "error": None,
            }
        if resp.status_code == 404:
            # 尚未发布 release：回退到 tags 列表取最新 tag
            logger.info("GitHub 无 release，回退 tags 接口")
            async with httpx.AsyncClient(timeout=6.0) as client:
                tags_resp = await client.get(
                    TAGS_API,
                    headers={"Accept": "application/vnd.github+json"},
                )
            if tags_resp.status_code == 200:
                tags = tags_resp.json()
                if tags:
                    latest_tag = str(tags[0].get("name", "")).lstrip("v")
                    return {
                        "has_update": parse_version(latest_tag) > parse_version(current),
                        "current": current,
                        "latest": latest_tag or None,
                        "release_url": f"https://github.com/{GITHUB_REPO}/tags",
                        "notes": None,
                        "error": None,
                    }
            return {
                "has_update": False,
                "current": current,
                "latest": None,
                "release_url": None,
                "notes": None,
                "error": "GitHub 仓库暂无可检测的版本（release/tag 为空）",
            }
        return {
            "has_update": False,
            "current": current,
            "latest": None,
            "release_url": None,
            "notes": None,
            "error": f"GitHub API 返回 HTTP {resp.status_code}",
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"检查更新失败: {exc}")
        return {
            "has_update": False,
            "current": current,
            "latest": None,
            "release_url": None,
            "notes": None,
            "error": f"检查更新失败: {exc}",
        }


async def run_update() -> dict[str, Any]:
    """执行 scripts/update.sh 进行一键升级。

    返回 started=True 表示脚本已开始执行；实际完成情况记录在 logs/upgrade.log，
    升级会重建并重启容器，期间面板会短暂不可用。
    """
    if not UPDATE_SCRIPT.exists():
        return {"started": False, "error": f"升级脚本不存在: {UPDATE_SCRIPT}"}

    # 只允许执行固定的 update.sh，不接收任意命令
    cmd = ["bash", str(UPDATE_SCRIPT)]
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        log = open(UPGRADE_LOG, "a", encoding="utf-8")  # noqa: SIM115
        log.write(f"\n===== 升级开始 {__import__('datetime').datetime.now()} =====\n")
        log.flush()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=log,
                stderr=log,
            )
            await proc.wait()
            log.write(f"\n===== 升级结束 exit={proc.returncode} =====\n")
        except Exception as exc:  # noqa: BLE001
            log.write(f"升级异常: {exc}\n")
        finally:
            log.close()

    asyncio.create_task(_run())
    return {
        "started": True,
        "log_file": str(UPGRADE_LOG),
        "message": "升级已在后台执行（git pull + 前端构建 + 容器重建），面板会短暂重启，请稍后刷新。",
    }
