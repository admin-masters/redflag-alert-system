import datetime, fastapi
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost", decode_responses=True)

MAX_OPENS = 10
MAX_SUBMITS = 2


async def check_open(phone: str):
    key = f"{phone}:{datetime.date.today()}:opens"
    if int(await redis_client.get(key) or 0) >= MAX_OPENS:
        raise fastapi.HTTPException(429, "Daily open limit reached")
    await redis_client.incr(key)


async def check_submit(phone: str):
    key = f"{phone}:{datetime.date.today()}:submits"
    if int(await redis_client.get(key) or 0) >= MAX_SUBMITS:
        raise fastapi.HTTPException(429, "Daily submit limit reached")
    await redis_client.incr(key)
