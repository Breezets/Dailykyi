#!/usr/bin/env bash
# ============================================================
# Dailykyi · 真正的 Docker 一键部署 / 升级脚本
#
# 用法（第一次部署 / 全新机器）：
#     bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh)
# 或将来域名可用：
#     bash <(curl -sSL https://get.dailykyi.cn)
#
# 用法（已部署实例升级 / 拉最新镜像 / 保留数据）：
#     bash <(curl -sSL ...) --upgrade
#
# 高级用法（自定义端口、默认账号、镜像名）：
#     curl -sSL ... | bash -s -- --port 8080 --username admin --password tv23333
#
# 支持的全部参数：
#   --port PORT            对外 HTTP 端口，默认 23333
#   --backend-port PORT    后端容器内部端口，默认 8000（一般不用改）
#   --username NAME        默认管理员用户名，默认 2233
#   --password PASS        默认管理员密码，默认 tv23333（首次登录建议改）
#   --secret KEY           JWT / Cookie 加密密钥，默认自动生成随机 32 位
#   --domain DOMAIN        若有公网域名，填入后打印时显示 https://DOMAIN:PORT
#   --upgrade              只执行升级：拉最新镜像并重启，不覆盖现有 .env 和数据
#   --uninstall            停止并移除 Dailykyi 容器（默认保留数据卷；加 --delete-data 才删）
#   --delete-data          与 --uninstall 同用：一并删除数据卷和数据库
#   --image-registry URL   镜像仓库前缀，默认 ghcr.io/breezets/dailykyi（可替换为自建 Harbor/Docker Hub）
#   --channel stable|edge  stable=latest tag；edge=main 分支 tag（开发版）
#   -y, --yes              所有交互确认都自动选择 Yes
#   -h, --help             显示本帮助
# ============================================================
set -uo pipefail

# ---------- 颜色 ----------
C_RED=$'\033[31m'; C_GREEN=$'\033[32m'; C_YELLOW=$'\033[33m'; C_CYAN=$'\033[36m'; C_BOLD=$'\033[1m'; C_RESET=$'\033[0m'
log_info()   { printf '%b[INFO]%b %s\n' "$C_CYAN" "$C_RESET" "$*"; }
log_ok()     { printf '%b[OK]%b   %s\n' "$C_GREEN" "$C_RESET" "$*"; }
log_warn()   { printf '%b[WARN]%b %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
log_error()  { printf '%b[ERR]%b  %s\n' "$C_RED" "$C_RESET" "$*"; }
banner() {
  cat <<'BANNER'

   _____      _ _       _                      _   _
  |  __ \    (_) |     | |                    | | (_)
  | |  | |_ __ _| |_   _| | ____ _   _   _ ___ | |_ _
  | |  | | '__| | | | | | |/ / _` | | | | / __|| __| |
  | |__| | |  | | | |_| |   < (_| | | |_| \__ \| |_| |
  |_____/|_|  |_|_|\__, |_|\_\__, |  \__, |___/ \__|_|
                    __/ |       __/ |   __/ |
                   |___/       |___/   |___/

   每日姬 Dailykyi —— 一键 Docker 部署脚本
   仓库：https://github.com/breezets/Dailykyi

BANNER
}

# ---------- 参数解析 ----------
PORT=23333
BACKEND_PORT=8000
USERNAME="2233"
PASSWORD="tv23333"
SECRET=""
DOMAIN=""
UPGRADE_ONLY=0
UNINSTALL=0
DELETE_DATA=0
REGISTRY="ghcr.io/breezets/dailykyi"
CHANNEL="stable"
AUTO_YES=0

usage() {
  sed -n '1,60p' "$0" | sed 's/^#/ /' | sed 's|^/usr/bin/env bash|Usage: |'
}

while [ $# -gt 0 ]; do
  case "$1" in
    --port)          PORT="$2"; shift 2 ;;
    --backend-port)  BACKEND_PORT="$2"; shift 2 ;;
    --username)      USERNAME="$2"; shift 2 ;;
    --password)      PASSWORD="$2"; shift 2 ;;
    --secret)        SECRET="$2"; shift 2 ;;
    --domain)        DOMAIN="$2"; shift 2 ;;
    --upgrade)       UPGRADE_ONLY=1; shift ;;
    --uninstall)     UNINSTALL=1; shift ;;
    --delete-data)   DELETE_DATA=1; shift ;;
    --image-registry) REGISTRY="${2%/}"; shift 2 ;;
    --channel)       CHANNEL="$2"; shift 2 ;;
    -y|--yes)        AUTO_YES=1; shift ;;
    -h|--help)       usage; exit 0 ;;
    --) shift; break ;;
    *) log_error "未知参数: $1  （-h 查看帮助）"; exit 2 ;;
  esac
done

confirm() {
  # $1 = prompt; AUTO_YES=1 时默认 yes
  if [ "$AUTO_YES" = "1" ]; then
    printf '%s [Y/n] %bY%b\n' "$1" "$C_GREEN" "$C_RESET"
    return 0
  fi
  printf '%s [Y/n] ' "$1"
  read -r ans
  case "$ans" in ""|y|Y|yes|Yes|YES) return 0 ;; *) return 1 ;; esac
}

banner
log_info "模式: $([ $UNINSTALL = 1 ] && echo 卸载 || ([ $UPGRADE_ONLY = 1 ] && echo 升级 || 全新部署))"

# ---------- 环境检查 ----------
need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log_error "缺少命令：$1  请先安装后再运行本脚本。"
    return 1
  fi
}
need_cmd docker || { log_info "安装指引：https://docs.docker.com/engine/install/"; exit 1; }
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  log_error "未检测到 docker compose（v2 或 v1）"; exit 1
fi
log_ok "环境检查通过：$($COMPOSE_CMD version --short 2>/dev/null || true)"

# Docker daemon
if ! docker info >/dev/null 2>&1; then
  log_error "无法连接 docker daemon（请先启动 docker 或将用户加入 docker 组后重新登录）"; exit 1
fi

# ---------- 工作目录 ----------
INSTALL_DIR="${DAILYKYI_INSTALL_DIR:-/opt/dailykyi}"
DATA_DIR="$INSTALL_DIR/data"
LOG_DIR="$INSTALL_DIR/logs"
COMPOSE_FILE="$INSTALL_DIR/docker-compose.yml"
ENV_FILE="$INSTALL_DIR/.env"

if [ "$UPGRADE_ONLY" = "0" ] && [ "$UNINSTALL" = "0" ]; then
  if [ -d "$INSTALL_DIR" ] && [ -f "$COMPOSE_FILE" ]; then
    log_warn "检测到 $INSTALL_DIR 已经存在部署"
    if confirm "是否在原目录上直接覆盖升级（保留 .env / 数据 / 日志）？"; then
      UPGRADE_ONLY=1
    else
      log_info "请指定其它目录运行：DAILYKYI_INSTALL_DIR=/path bash <(curl -sSL ...)"; exit 0
    fi
  fi
fi

# ---------- 卸载 ----------
if [ "$UNINSTALL" = "1" ]; then
  if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "未找到 $COMPOSE_FILE，似乎本机器上尚未通过本脚本部署 Dailykyi。"
    exit 1
  fi
  log_warn "将执行：$COMPOSE_CMD down（删除容器/网络，默认保留数据卷）"
  if [ "$DELETE_DATA" = "1" ]; then
    log_warn "  且 --delete-data 已指定：将一并删除 $INSTALL_DIR 下所有数据、日志与配置"
  fi
  if confirm "确认卸载？" ; then
    ( cd "$INSTALL_DIR" && $COMPOSE_CMD down )
    if [ "$DELETE_DATA" = "1" ]; then
      log_info "删除 $INSTALL_DIR ..."
      rm -rf "$INSTALL_DIR" || true
    fi
    log_ok "卸载完成。"
  else
    log_info "用户取消卸载。"
  fi
  exit 0
fi

# ---------- 通道 / TAG ----------
TAG="latest"
[ "$CHANNEL" = "edge" ] && TAG="main"
BACKEND_IMAGE="${REGISTRY}/backend:${TAG}"
FRONTEND_IMAGE="${REGISTRY}/nginx:${TAG}"

# 若 ghcr.io/breezets/dailykyi 暂未推送镜像，回退 Docker Hub 兜底地址（保留用户自定义 registry 不覆盖）
FALLBACK_BACKEND="breezets/dailykyi-backend:${TAG}"
FALLBACK_FRONTEND="breezets/dailykyi-nginx:${TAG}"

mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$LOG_DIR"
cd "$INSTALL_DIR" || { log_error "cd $INSTALL_DIR 失败"; exit 1; }

# ---------- 密钥 / .env ----------
if [ "$UPGRADE_ONLY" = "0" ] || [ ! -f "$ENV_FILE" ]; then
  [ -z "$SECRET" ] && SECRET="$(docker run --rm alpine:3.20 apk add --no-cache openssl >/dev/null 2>&1 && openssl rand -base64 48 || head -c 48 /dev/urandom | base64 | tr -d '\n')"
  # 上面 openssl 子容器生成较慢，给一个纯本地保底
  [ -z "$SECRET" ] && SECRET="$(head -c 64 /dev/urandom | base64 | tr -d '\n')"
  : > "$ENV_FILE"
  {
    echo "# Dailykyi 由 install-docker.sh 自动生成于 $(date '+%Y-%m-%d %H:%M:%S')"
    echo "DAILYKYI_APP_VERSION_FROM_INSTALLER=docker-oneclick"
    echo "DAILYKYI_DEFAULT_USERNAME=$USERNAME"
    echo "DAILYKYI_DEFAULT_PASSWORD=$PASSWORD"
    echo "DAILYKYI_SECRET_KEY=$SECRET"
    echo "DAILYKYI_DATABASE_URL=sqlite+aiosqlite:///data/dailykyi.db"
    echo "DAILYKYI_TIMEZONE=Asia/Shanghai"
    echo "DAILYKYI_PORT=$PORT"
    echo "DAILYKYI_BACKEND_PORT=$BACKEND_PORT"
  } >> "$ENV_FILE"
  log_ok "已生成 .env：$ENV_FILE（默认账号 $USERNAME / 密码已写入并仅本机可读）"
  chmod 600 "$ENV_FILE"
fi

# ---------- docker-compose.yml（用于一键部署的纯镜像版 compose，不包含 build: 字段）----------
write_compose() {
  cat > "$COMPOSE_FILE" <<YAML
# Dailykyi · 一键脚本生成的纯镜像版 compose。不依赖源码，也不执行本地 build。
# 若将来要替换自定义镜像：直接改 image 字段，然后：docker compose pull && docker compose up -d
services:
  backend:
    image: ${BACKEND_IMAGE}
    container_name: dailykyi-backend
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      # bind-mount 整个 /opt/dailykyi 到容器 /host：一键升级时可以读 ./scripts（本脚本会把 update.sh 放进 /opt/dailykyi/scripts/）
      - ./:/host
      - /var/run/docker.sock:/var/run/docker.sock
    env_file:
      - .env
    environment:
      - DAILYKYI_DATABASE_URL=\${DAILYKYI_DATABASE_URL:-sqlite+aiosqlite:///data/dailykyi.db}
      - TZ=\${DAILYKYI_TIMEZONE:-Asia/Shanghai}
      - DAILYKYI_HOST_PROJECT_DIR=/host
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:\${DAILYKYI_BACKEND_PORT:-8000}/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    networks:
      - dailykyi-net

  nginx:
    image: ${FRONTEND_IMAGE}
    container_name: dailykyi-nginx
    restart: unless-stopped
    ports:
      - "\${DAILYKYI_PORT:-23333}:80"
    depends_on:
      - backend
    networks:
      - dailykyi-net

networks:
  dailykyi-net:
    driver: bridge
YAML
}

if [ "$UPGRADE_ONLY" = "0" ] || [ ! -f "$COMPOSE_FILE" ]; then
  write_compose
  log_ok "已生成 docker-compose.yml：$COMPOSE_FILE"
fi

# 镜像拉取：尝试主 registry，失败则回退 Docker Hub 镜像 tag 并写入 compose（避免下次还失败）
pull_images() {
  local backend_used="$BACKEND_IMAGE"
  local frontend_used="$FRONTEND_IMAGE"
  log_info "拉取后端镜像：$backend_used"
  if ! docker pull "$backend_used"; then
    log_warn "主 registry 拉取失败，回退 Docker Hub：$FALLBACK_BACKEND"
    BACKEND_IMAGE="$FALLBACK_BACKEND"
    FRONTEND_IMAGE="$FALLBACK_FRONTEND"
    docker pull "$BACKEND_IMAGE" || return 1
    docker pull "$FRONTEND_IMAGE" || return 1
    # 回退写入 compose（持久化）
    write_compose
  else
    log_info "拉取前端镜像：$frontend_used"
    if ! docker pull "$frontend_used"; then
      log_warn "主 registry 拉取失败，回退 Docker Hub：$FALLBACK_FRONTEND"
      BACKEND_IMAGE="$FALLBACK_BACKEND"
      FRONTEND_IMAGE="$FALLBACK_FRONTEND"
      docker pull "$BACKEND_IMAGE" || true
      docker pull "$FRONTEND_IMAGE" || true
      write_compose
    fi
  fi
  return 0
}

pull_images || {
  log_error "镜像拉取失败。检查网络后可重跑：bash <(curl -sSL ...) --upgrade"; exit 1
}

# 放一份 update.sh 到宿主 /opt/dailykyi/scripts/，方便：
#   1) 面板里一键升级按钮（后端 bind-mount /host 后能读到）
#   2) 手动升级：bash /opt/dailykyi/scripts/update.sh --image-only
mkdir -p "$INSTALL_DIR/scripts"
if ! command -v scripts/update.sh >/dev/null 2>&1; then
  # 直接嵌入一个最小可用的 update.sh 副本（镜像模式），避免又去 raw 依赖网络
  cat > "$INSTALL_DIR/scripts/update.sh" <<'SCRIPT'
#!/usr/bin/env bash
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${DAILYKYI_HOST_PROJECT_DIR:-$(dirname "$SCRIPT_DIR")}"
cd "$ROOT_DIR" || exit 1
COMPOSE_CMD="docker compose"
docker compose version >/dev/null 2>&1 || COMPOSE_CMD="docker-compose"
echo "==> Dailykyi 纯镜像模式升级"
$COMPOSE_CMD pull
$COMPOSE_CMD up -d
echo "✅ 完成：$COMPOSE_CMD ps"
SCRIPT
  chmod +x "$INSTALL_DIR/scripts/update.sh"
fi

# ---------- 启动 ----------
log_info "启动 Dailykyi..."
$COMPOSE_CMD up -d

# ---------- 健康检查 ----------
log_info "等待容器健康（最多 60s）..."
timeout 60 bash -c "until $COMPOSE_CMD exec -T backend curl -fsS http://localhost:${BACKEND_PORT}/api/v1/health >/dev/null 2>&1; do sleep 2; done" \
  && log_ok "后端健康检查通过" || log_warn "健康检查超时，可手动查看：$COMPOSE_CMD logs backend"

# ---------- 输出访问地址 / 凭证 ----------
ACCESS_HOST="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -z "$ACCESS_HOST" ] && ACCESS_HOST="127.0.0.1"
URL_SCHEME="http"
URL_HOST="$ACCESS_HOST"
[ -n "$DOMAIN" ] && URL_HOST="$DOMAIN"
ADDR="${URL_SCHEME}://${URL_HOST}:${PORT}"

echo ""
echo "  $C_BOLD━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$C_RESET"
echo "  $C_GREEN🎉 Dailykyi $([ $UPGRADE_ONLY = 1 ] && echo 已升级 || 已部署)$C_RESET  $C_CYAN$CHANNEL$C_RESET"
echo "  $C_BOLD━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$C_RESET"
echo ""
echo "    面板地址   : $C_BOLD$ADDR$C_RESET"
echo "    默认账号   : $USERNAME"
echo "    默认密码   : $PASSWORD  （首次登录后请立即在【系统设置→安全】里修改）"
echo "    安装目录   : $INSTALL_DIR"
echo "    配置文件   : $COMPOSE_FILE"
echo "    环境变量   : $ENV_FILE"
echo ""
echo "    常用命令："
echo "      • 查看状态     $COMPOSE_CMD -f $COMPOSE_FILE ps"
echo "      • 查看日志     $COMPOSE_CMD -f $COMPOSE_FILE logs -f"
echo "      • 立即升级     bash <(curl -sSL https://raw.githubusercontent.com/breezets/Dailykyi/main/scripts/install-docker.sh) --upgrade"
echo "      • 手动升级     bash $INSTALL_DIR/scripts/update.sh --image-only"
echo "      • 卸载         bash <(curl -sSL ...) --uninstall  [--delete-data]"
echo "  $C_BOLD━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$C_RESET"
