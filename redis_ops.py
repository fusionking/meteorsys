from typing import Optional

import redis

redis_client = redis.Redis()


def save_to_redis(key: str, value: str, ex: int = None):
    redis_client.set(key, value, ex=ex)


def get_from_redis(key: str) -> Optional[str]:
    value = redis_client.get(key)
    if not value:
        value = redis_client.get(key.lower())
    return value.decode("utf-8") if value else value
