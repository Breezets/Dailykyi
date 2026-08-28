#!/usr/bin/env bash
# ============================================================
# Dailykyi 一键升级脚本（Linux / macOS）
# 用法: bash scripts/update.sh [--image-only]
#   --image-only  即使当前有 git 仓库，也强制走『拉最新镜像并重启容器』
#
# 支持两种部署形态（脚本自动识别，也可被环境变量覆盖）：
#   1) 源码部署（仓库根存在 .git / docker-compose.yml）：
#        git pull → 安装前端依赖并 build → docker compose build backend → up -d
#   2) 纯镜像部署（一键脚本部署出来的实例，没有源码）：
#        docker compose pull → docker compose up -d
#        如果没有 compose 文件则直接 docker pull 官方镜像 + 重启容器
#
# 常用环境变量：
#   DAILYKYI_HOST_PROJECT_DIR   宿主项目根（后端通过 bind-mount 传入）
#   DAILYKYI_GITHUB_REPO        默认 breezets/Dailykyi（用于未指定镜像时构造 tag）
#   DAILYKYI_IMAGE_BACKEND      后端镜像名（默认 ghcr.io/breezets/dailykyi/backend）
#   DAILYKYI_IMAGE_FRONTEND     前端/nginx 镜像名（默认 ghcr.io/breezets/dailykyi/nginx）
# ============================================================
set -uo pipefail

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# ---------- 定位宿主机项目根 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
# 后端服务会把宿主项目根以 DAILYKYI_HOST_PROJECT_DIR 传入；若有则优先用它（真正的宿主机工作目录）
if [ -n "${DAILYKYI_HOST_PROJECT_DIR:-}" ] && [ -d "$DAILYKYI_HOST_PROJECT_DIR" ]; then
  ROOT_DIR="$DAILYKYI_HOST_PROJECT_DIR"
fi
cd "$ROOT_DIR" || { log "✗ 无法 cd 到 $ROOT_DIR"; exit 1; }

IMAGE_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --image-only) IMAGE_ONLY=1 ;;
    -h|--help)
      sed -n '1,20p' "$0"
      exit 0
      ;;
  esac
done

GITHUB_REPO="${DAILYKYI_GITHUB_REPO:-breezets/Dailykyi}"
BACKEND_IMAGE="${DAILYKYI_IMAGE_BACKEND:-ghcr.io/${GITHUB_REPO}/backend}"
FRONTEND_IMAGE="${DAILYKYI_IMAGE_FRONTEND:-ghcr.io/${GITHUB_REPO}/nginx}"

# ---------- 环境检查 ----------
log "==> 工作目录: $ROOT_DIR"
command -v docker >/dev/null 2>&1 || { log "✗ 未安装 docker"; exit 1; }
if ! docker compose version >/dev/null 2>&1; then
  # 兼容老的 docker-compose v1
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
  else
    log "✗ 未检测到 docker compose（v2 或 v1）"; exit 1
  fi
else
  COMPOSE_CMD="docker compose"
fi

HAS_GIT=0
[ -d .git ] && command -v git >/dev/null 2>&1 && HAS_GIT=1
HAS_COMPOSE=0
[ -f docker-compose.yml ] && HAS_COMPOSE=1
HAS_SOURCE=0
[ -f backend/requirements.txt ] && [ -f frontend/package.json ] && HAS_SOURCE=1

log "    - git 仓库：$([ $HAS_GIT = 1 ] && echo 是 || echo 否)"
log "    - compose 文件：$([ $HAS_COMPOSE = 1 ] && echo 是 || echo 否)"
log "    - 源码结构：$([ $HAS_SOURCE = 1 ] && echo 是 || echo 否)"

# ---------- 决策运行模式 ----------
MODE="source"
if [ "$IMAGE_ONLY" = "1" ]; then
  MODE="image"
elif [ "$HAS_SOURCE" = "0" ] || [ "$HAS_GIT" = "0" ]; then
  # 没有源码 → 必然走镜像拉取模式（一键脚本部署的标准形态）
  MODE="image"
fi
log "==> 升级模式: $MODE"

upgrade_image() {
  log "==> 拉取最新镜像（$BACKEND_IMAGE, $FRONTEND_IMAGE）"
  if [ "$HAS_COMPOSE" = "1" ]; then
    log "    方式 A：有 compose 文件 → docker compose pull && up -d"
    $COMPOSE_CMD pull || {
      # compose pull 失败也不一定致命（可能 build:./backend 而 image 字段缺失），回退手动拉取
      log "⚠   compose pull 失败，尝试单独 docker pull 两个镜像…"
      docker pull "$BACKEND_IMAGE:latest" || true
      docker pull "$FRONTEND_IMAGE:latest" || true
    }
    $COMPOSE_CMD up -d
  else
    log "    方式 B：无 compose 文件 → 直接 docker pull + 滚动重启现有同名容器"
    docker pull "$BACKEND_IMAGE:latest" || true
    docker pull "$FRONTEND_IMAGE:latest" || true
    for c in dailykyi-backend dailykyi-nginx; do
      if docker ps -a --format '{{.Names}}' | grep -q "^${c}\$"; then
        img="$(docker inspect --format='{{.Config.Image}}' "$c" 2>/dev/null || true)"
        log "    - 容器 $c 使用镜像: ${img:-<unknown>}，执行重启"
        docker restart "$c" || true
      fi
    done
  fi
  log "✅ 镜像升级完成（若容器未自重启请手动：$COMPOSE_CMD up -d）"
}

upgrade_source() {
  log "==> git pull 拉取最新代码"
  if ! git pull --ff-only origin main 2>update.err; then
    log "⚠   git pull 失败："
    cat update.err || true
    rm -f update.err
    log ""
    log "  如果提示 TLS/网络错误，可切换 SSH 方式后重试："
    log "    git remote set-url origin git@github.com:${GITHUB_REPO}.git"
    log "  或尝试强制使用镜像升级：bash scripts/update.sh --image-only"
    exit 1
  fi
  rm -f update.err

  log "==> 构建前端"
  if [ -d frontend ] && command -v npm >/dev/null 2>&1; then
    ( cd frontend && npm install --no-audit --no-fund --loglevel=error && npm run build ) \
      || { log "✗ 前端构建失败"; exit 1; }
  else
    log "⚠   缺少前端构建环境（npm 或 frontend 目录），跳过前端构建。"
    log "    建议改用：bash scripts/update.sh --image-only（直接拉现成镜像）"
  fi

  if [ "$HAS_COMPOSE" = "1" ]; then
    log "==> 重建后端镜像并重启服务（数据卷保留）"
    $COMPOSE_CMD build backend || log "⚠   build backend 失败，尝试直接 up -d 复用现有镜像"
    $COMPOSE_CMD up -d
  else
    log "==> 无 compose 文件，尝试重启 dailykyi 容器"
    for c in dailykyi-backend dailykyi-nginx; do
      docker ps -a --format '{{.Names}}' | grep -q "^${c}\$" && docker restart "$c" || true
    done
  fi
}

case "$MODE" in
  image)  upgrade_image ;;
  source) upgrade_source ;;
esac

echo ""
log "============================================"
log "✅ 升级完成！访问 http://<服务器IP>:23333 即可"
log "   若容器名或端口不同，使用：$COMPOSE_CMD ps"
log "   查看运行日志：$COMPOSE_CMD logs -f"
log "   若仍停在旧版本：再执行一次 bash scripts/update.sh --image-only"
