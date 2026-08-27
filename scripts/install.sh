#!/usr/bin/env bash
# ============================================================
# Dailykyi 一键部署脚本（Linux / macOS）
# 用法: bash scripts/install.sh
# 要求: git + docker + docker compose v2
# ============================================================
set -euo pipefail

# ---------- 目录定位 ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# ---------- 环境检查 ----------
echo "==> 检查环境..."
command -v git >/dev/null 2>&1 || { echo "✗ 未安装 git，请先安装"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "✗ 未安装 docker，请先安装"; exit 1; }
if ! docker compose version >/dev/null 2>&1; then
  echo "✗ 未检测到 docker compose v2，请先安装"; exit 1
fi
echo "✓ git / docker / docker compose 均就绪"

# ---------- 环境变量 ----------
if [ ! -f .env ]; then
  echo "==> 未发现 .env，从模板复制（请按需修改密钥与默认密码）"
  cp .env.example .env
  echo "    已生成 .env"
else
  echo "==> .env 已存在，跳过"
fi

# ---------- 构建前端 ----------
if [ ! -d frontend ]; then
  echo "✗ 缺少 frontend 目录，请在项目根目录执行"; exit 1
fi
echo "==> 构建前端（npm install + build）"
cd frontend
if ! command -v npm >/dev/null 2>&1; then
  echo "✗ 未安装 npm / node，请先安装 Node.js 18+" ; exit 1
fi
npm install
npm run build
cd ..

# ---------- 启动 ----------
echo "==> 构建并启动服务"
docker compose up -d --build

echo ""
echo "✅ Dailykyi 部署完成！"
echo "   访问地址: http://<服务器IP>:23333"
echo "   默认账号: 2233（.env 中 DAILYKYI_DEFAULT_USERNAME）"
echo "   默认密码: 见 .env 中 DAILYKYI_DEFAULT_PASSWORD（首次登录后强制修改）"
echo ""
echo "   查看日志: docker compose logs -f"
