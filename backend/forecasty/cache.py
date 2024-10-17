import os
import json
import redis
import hashlib

from pydantic import BaseModel
from datetime import datetime, timezone


class _FuncCached(BaseModel):
    timestamp: int
    output: str


class MemCache:
    def __init__(self, redis_connection):
        self._r = redis_connection

    def _hash_func_args(self, args: tuple, kwargs: dict) -> str:
        args_hash = hashlib.new("sha256")
        args_hash.update(hash(args).to_bytes())
        args_hash.update(hash(json.dumps(kwargs)).to_bytes())
        return args_hash.hexdigest()

    def key_func(self, args: tuple, kwargs: dict):
        return f"func:{self._hash_func_args(args, kwargs)}"

    def cache_func(self, key: str, output: str):
        timestamp = datetime.now(timezone.utc).timestamp()
        self._r.set(
            key, _FuncCached(timestamp=timestamp, output=output).model_dump_json()
        )

    def get_func(self, key: str) -> _FuncCached:
        return _FuncCached.model_validate_json(self._r.get(key))

    def erase_func(self, key):
        self._r.delete(key)


def get_redis_connection_params():
    REDIS_HOST_FALLBACK = "localhost"
    REDIS_PORT_FALLBACK = 6379
    REDIS_PASSWORD_FALLBACK = "toor"

    REDIS_HOST = os.getenv("REDIS_HOST", REDIS_HOST_FALLBACK)
    REDIS_PORT = os.getenv("REDIS_PORT", REDIS_PORT_FALLBACK)
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", REDIS_PASSWORD_FALLBACK)

    return {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "password": REDIS_PASSWORD,
        "decode_responses": True,
    }


_r = redis.Redis(**get_redis_connection_params())

_memcache = MemCache(_r)


def cached(func):
    def wrapper(*args, **kwargs):
        key = _memcache.key_func(args, kwargs)
        if cached_output := _memcache.get_func(key):
            return cached_output
        output = func(*args, **kwargs)
        _memcache.cache_func(key, output)
        return output

    return wrapper
