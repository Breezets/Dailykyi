#!/usr/bin/env python3
"""首次部署时初始化 SQLite 数据库并创建所有表。

用法：
    python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# 将 backend 目录加入模块搜索路径
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import init_db


async def main() -> None:
    # 确保数据库文件所在目录存在（兼容容器与本地直接运行）
    db_url = settings.DATABASE_URL
    prefix = "sqlite+aiosqlite:///"
    if db_url.startswith(prefix):
        db_path = Path(db_url[len(prefix):])
        db_path.resolve().parent.mkdir(parents=True, exist_ok=True)
    await init_db()
    print("数据库初始化完成")


if __name__ == "__main__":
    asyncio.run(main())
