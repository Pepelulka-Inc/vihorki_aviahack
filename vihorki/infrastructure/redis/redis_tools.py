import logging
from typing import AsyncGenerator, AnyStr
from contextlib import asynccontextmanager
from datetime import timedelta

import orjson
from redis.asyncio import Redis, RedisCluster
from redis.cluster import ClusterNode

from vihorki.domain.entities.cached_message import CachedMetric


logger = logging.getLogger(__name__)


@asynccontextmanager
async def redis_conn_context(
    redis_host: str,
    redis_port: str,
    redis_user: str | None = None,
    redis_password: str | None = None,
    redis_is_cluster: bool = False,
) -> AsyncGenerator[RedisCluster | Redis, None]:
    if redis_is_cluster:
        conn = RedisCluster(
            startup_nodes=[ClusterNode(host=host, port=redis_port) for host in redis_host.split(',')],
            username=redis_user,
            password=redis_password,
            decode_responses=True,
        )
        await conn.initialize()
    else:
        conn = Redis(host=redis_host, port=redis_port, decode_responses=True)
        await conn.initialize()
    try:
        yield conn
    finally:
        await conn.close()


class RedisCache:
    def __init__(self, cache_client: Redis | RedisCluster):
        self._cache_client = cache_client

    async def set_value(self, key: str, value: AnyStr, ex: int | timedelta | None = None):
        await self._cache_client.set(key, value, ex=ex)

    async def get_value(self, key: str) -> CachedMetric:
        value = await self._cache_client.get(key)
        try:
            return CachedMetric(key=key, value=orjson.loads(value))
        except orjson.JSONDecodeError:
            logger.error('Wrong redis value: %s', value)
            raise
