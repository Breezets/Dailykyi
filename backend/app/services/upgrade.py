"""版本升级检测与一键升级服务（v0.2.5 修正版）。

- check_update: 调用 GitHub Releases API 与当前版本比较
- run_update: 优先使用「宿主机项目根」下的 scripts/update.sh（docker 部署已通过 bind-mount
  把项目根挂进 /host），否则回退容器内 /app/scripts/update.sh，再回退仓库根脚本；
  纯镜像一键部署（没有源码）时，update.sh 会自动走「docker pull → up -d」分支，
  不再出现「升级脚本不存在: /scripts/update.sh」。
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from app.config import BASE_DIR, LOG_DIR, settings

# 开源仓库（发布新版本时保持与 README 一致）
GITHUB_REPO = "breezets/Dailykyi"
RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TAGS_API = f"https://api.github.com/repos/{GITHUB_REPO}/tags"


def _candidate_script_paths() -> list[Path]:
    """按优先级列出 update.sh 的可能位置。

    1) 用户在 .env 里配置的 HOST_PROJECT_DIR/scripts/update.sh（推荐：容器里 /host）
    2) 容器内 /host/scripts/update.sh（默认 bind-mount 路径，v0.2.5 起 docker-compose.yml 自带）
    3) 容器镜像里 /app/scripts/update.sh（v0.2.5 起 Dockerfile COPY scripts 进镜像兜底）
    4) 基于 BASE_DIR.parent 的仓库根 scripts/update.sh（直接本地开发跑 python 时命中）
    5) 真实的仓库根（backend 目录的上级，比 BASE_DIR 再往上一层）/scripts/update.sh
       —— 兼容 v0.2.0/v0.2.1 时期写死 BASE_DIR.parent 的历史代码
    """
    configured = (getattr(settings, "HOST_PROJECT_DIR", "") or "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured) / "scripts" / "update.sh")
    candidates.append(Path("/host") / "scripts" / "update.sh")
    candidates.append(Path("/app") / "scripts" / "update.sh")
    candidates.append(BASE_DIR.parent / "scripts" / "update.sh")
    # backend/ 下如果是真实仓库根（存在 .git / docker-compose.yml），其上一级 = 项目根
    candidates.append(BASE_DIR.parent.parent / "scripts" / "update.sh")
    # 去重（保留顺序）
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in candidates:
        try:
            s = str(p.resolve())
        except Exception:  # noqa: BLE001
            s = str(p)
        if s in seen:
            continue
        seen.add(s)
        uniq.append(p)
    return uniq


def _resolve_update_script() -> tuple[Path | None, list[str]]:
    """按优先级找 update.sh；返回 (命中路径, 所有搜索过的路径列表用于报错可读)。"""
    checked: list[str] = []
    for p in _candidate_script_paths():
        checked.append(str(p))
        if p.exists():
            return p, checked
    return None, checked


UPDATE_SCRIPT, _SEARCHED_PATHS = _resolve_update_script()
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
    """执行 update.sh 进行一键升级。

    脚本支持两种模式：
    - 源码模式（项目根存在 .git）：git pull → 构建前端 → docker compose build/up -d
    - 纯镜像模式（例如一键脚本部署出来的实例）：docker compose pull → docker compose up -d
      或回退为 docker pull 官方镜像后重启容器。

    返回 started=True 表示脚本已开始执行；实际完成情况记录在 logs/upgrade.log，
    升级会重建并重启容器，期间面板会短暂不可用。
    """
    # 每次点击都重新解析（允许用户之后补 bind-mount 后不用重启容器即可生效）
    script_path, searched = _resolve_update_script()
    if script_path is None:
        lines = [
            f"升级脚本不存在：依次查找了 {len(searched)} 个位置均未找到 scripts/update.sh。",
            "  → 已搜索位置：",
        ]
        for p in searched:
            lines.append(f"     • {p}")
        lines += [
            "",
            "解决方法（任选其一）：",
            "  1. 推荐：把项目根用 docker-compose bind-mount 进 /host（v0.2.5 起的 compose 默认就做了），",
            "     然后执行：docker compose up -d backend；再在界面点一键升级即可。",
            "  2. 如果你是『docker 一键脚本部署』（只有镜像，没有源码）：",
            "     请在服务器上运行：bash <(curl -sSL https://get.dailykyi.cn) --upgrade",
            "     或直接：docker compose pull && docker compose up -d",
            "  3. 临时手动：把官方 scripts/update.sh 下载到服务器任意路径后，在 .env 里配置",
            "     DAILYKYI_HOST_PROJECT_DIR=<父目录>，重启容器后再点升级按钮。",
        ]
        err_msg = "\n".join(lines)
        logger.warning(err_msg)
        return {"started": False, "error": err_msg}

    # 只允许执行 update.sh，不接收任意命令；并传递宿主项目根 env 给脚本
    root_dir = str(script_path.parent.parent)
    env = os.environ.copy()
    env["DAILYKYI_HOST_PROJECT_DIR"] = root_dir
    cmd = ["bash", str(script_path)]
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    async def _run() -> None:
        log = open(UPGRADE_LOG, "a", encoding="utf-8")  # noqa: SIM115
        log.write(f"\n===== 升级开始 {__import__('datetime').datetime.now()} =====\n")
        log.write(f"脚本路径: {script_path}\n")
        log.write(f"宿主项目根(推断): {root_dir}\n")
        log.flush()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=log,
                stderr=log,
                env=env,
                cwd=root_dir,
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
        "script_used": str(script_path),
        "message": "升级已在后台执行，面板会短暂重启后刷新。详情可在系统设置→调试与诊断→日志查看器筛选 'upgrade'。",
    }
