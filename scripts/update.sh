#!/usr/bin/env bash
# ============================================================
# Dailykyi 一键升级脚本（Linux / macOS）
# 用法: bash scripts/update.sh
# 作用: git pull → 构建前端 → 重建后端 → 重启服务（数据保留）
# ============================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo "==> 检查环境..."
command -v git >/dev/null 2>&1 || { echo "✗ 未安装 git"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "✗ 未安装 docker"; exit 1; }
if ! docker compose version >/dev/null 2>&1; then
  echo "✗ 未检测到 docker compose v2"; exit 1
fi

if [ ! -d .git ]; then
  echo "✗ 当前目录不是 git 仓库，无法自动升级。"
  echo "  请改用：手动替换源码后执行 docker compose up -d --build"
  exit 1
fi

# ---------- 拉取最新代码 ----------
echo "==> git pull 拉取最新代码"
if ! git pull --ff-only origin main 2>update.err; then
  echo "⚠  git pull 失败："
  cat update.err
  rm -f update.err
  echo ""
  echo "  如果提示 TLS/网络错误，可切换 SSH 方式后重试："
  echo "    git remote set-url origin git@github.com:breezets/Dailykyi.git"
  exit 1
fi
rm -f update.err

# ---------- 构建前端 ----------
echo "==> 构建前端"
cd frontend
npm install
npm run build
cd ..

# ---------- 重建后端并重启 ----------
echo "==> 重建后端镜像并重启服务（数据卷保留）"
docker compose build backend
docker compose up -d

echo ""
echo "✅ 升级完成！当前版本：$(grep 'APP_VERSION' backend/app/config.py | head -1)"
echo "   如果后端新增了数据库字段，启动时会自动补充，无需手动迁移。"
echo "   查看升级日志: docker compose logs -f"
