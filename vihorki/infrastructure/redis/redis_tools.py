import json
import logging
from typing import AsyncGenerator, AnyStr
from contextlib import asynccontextmanager
from datetime import timedelta

from redis.asyncio import Redis, RedisCluster
from redis.cluster import ClusterNode

from domain.entities.cached_message import CachedMetric


logger = logging.getLogger(__name__)


@asynccontextmanager
async def redis_conn_context(
    redis_host: str, redis_port: str, redis_user: str | None, redis_password: str | None, redis_is_cluster: bool = False
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
    cache_client: Redis | RedisCluster

    async def set_value(self, key: str, value: AnyStr, ex: int | timedelta | None = None):
        await self.cache_client.set(key, value, ex=ex)

    async def get_value(self, key: str) -> CachedMetric:
        value = await self.cache_client.get(key)
        try:
            return CachedMetric(key=key, value=json.loads(value))
        except json.JSONDecodeError:
            logger.error('Wrong redis value: %s', value)
            raise
