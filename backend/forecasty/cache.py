import os
import json
import redis
import hashlib
import logging

from pydantic import BaseModel
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class _FuncCacheDump(BaseModel):
    timestamp: int
    output: str


class MemCache:
    def __init__(self, redis_connection):
        self._r = redis_connection

    def _hash_func_args(self, args: tuple, kwargs: dict) -> str:
        args_hash = hashlib.md5()  # md5's greatly faster than sha256, so use it
        args_hash.update(str(hash(args)).encode("utf-8"))
        args_hash.update(str(hash(json.dumps(kwargs))).encode("utf-8"))
        return args_hash.hexdigest()

    def func_key(self, func, args: tuple, kwargs: dict):
        """
        Generates unique function key to cache it in this format:
        func:`function-human-readable-name`:`function-hash`(`function-arguments-hash`)
        """

        return f"func:{func.__qualname__}:{self._hash_func_args(args, kwargs)}"

    def cache_func(self, key: str, timestamp: int, output: str):
        self._r.set(
            key, _FuncCacheDump(timestamp=timestamp, output=output).model_dump_json()
        )

    def get_func(self, key: str) -> _FuncCacheDump | None:
        dump = self._r.get(key)
        if dump is None:
            return None
        return _FuncCacheDump.model_validate_json(dump)

    def erase_func(self, key):
        self._r.delete(key)


def get_redis_connection_params():
    REDIS_HOST_FALLBACK = "redis"
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

_TRIGGER_CALL_SECS = 2 * 3600  # two hours


def cached(func):
    def wrapper(*args, **kwargs):
        key = _memcache.func_key(func, args, kwargs)
        if dump := _memcache.get_func(key):
            call_dt = datetime.fromtimestamp(float(dump.timestamp), timezone.utc)
            current_dt = datetime.now(timezone.utc)
            delta = current_dt - call_dt
            if delta.total_seconds() <= _TRIGGER_CALL_SECS:
                logger.info(f"Got {key} output from cache")
                return json.loads(dump.output)
        output = func(*args, **kwargs)
        timestamp = int(round(datetime.now(timezone.utc).timestamp()))
        _memcache.cache_func(key, timestamp, json.dumps(output))
        logger.info(f"Cached {key} output")
        return output

    return wrapper
