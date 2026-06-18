import redis.asyncio as redis
from app.config import settings

redis_client = redis.from_url(settings.redis_url, decode_responses=True)  # pragma: no cover

async def get_redis():
    return redis_client
