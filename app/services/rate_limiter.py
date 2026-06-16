import time
from app.redis_client import get_redis
from app.config import settings

async def check_rate_limit(account_id: str, redis_client=None) -> bool:
    if redis_client is None:
        redis_client = await get_redis()
    key = f"rate_limit:{account_id}"
    now = time.time()
    window_start = now - settings.rate_limit_window_seconds

    await redis_client.zremrangebyscore(key, 0, window_start)
    count = await redis_client.zcard(key)
    if count >= settings.rate_limit_max_requests:
        return False
    await redis_client.zadd(key, {str(now): now})
    await redis_client.expire(key, settings.rate_limit_window_seconds * 2)
    return True
