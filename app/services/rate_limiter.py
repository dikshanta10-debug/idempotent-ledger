import time
from app.redis_client import get_redis
from app.config import settings

async def check_rate_limit(account_id: str) -> bool:
    redis = await get_redis()
    key = f"rate_limit:{account_id}"
    now = time.time()
    window_start = now - settings.rate_limit_window_seconds

    await redis.zremrangebyscore(key, 0, window_start)
    count = await redis.zcard(key)
    if count >= settings.rate_limit_max_requests:
        return False
    await redis.zadd(key, {str(now): now})
    await redis.expire(key, settings.rate_limit_window_seconds * 2)
    return True
