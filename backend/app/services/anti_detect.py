"""反检测：随机延迟，模拟真实用户操作间隔。"""

import asyncio
import random


async def random_delay(min_sec: float, max_sec: float) -> float:
    """在 [min_sec, max_sec] 范围内随机等待，返回实际等待秒数。"""
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)
    return delay
