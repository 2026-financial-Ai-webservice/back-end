from redis.asyncio import Redis

from app.core.config import settings

#redis 클라이언트 생성
redis_client = Redis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def close_redis() -> None:
    await redis_client.aclose()