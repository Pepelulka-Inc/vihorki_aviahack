import asyncio
import logging

from aiohttp import web

from vihorki.infrastructure.postgres.on_startup.run_db import init_db_and_tables
from vihorki.infrastructure.redis.redis_tools import redis_conn_context, RedisCache

from vihorki.infrastructure.settings import REDIS_HOST, REDIS_IS_CLUSTER, REDIS_PASSWORD, REDIS_PORT, REDIS_USER

logger = logging.getLogger(__name__)


async def on_startup(app):
    try:
        await init_db_and_tables()
        logger.info('Successfully setup db')
    except Exception as e:
        logger.error(f'Ошибка инициализации БД: {e}')
        raise


async def healthcheck(request):
    health_data = {'status': 'healthy', 'timestamp': asyncio.get_event_loop().time(), 'service': 'vihorki'}
    async with redis_conn_context(
        redis_host=REDIS_HOST,
        redis_port=REDIS_PORT,
        redis_user=REDIS_USER,
        redis_password=REDIS_PASSWORD,
        redis_is_cluster=REDIS_IS_CLUSTER,
    ) as redis_cache:
        cache = RedisCache(redis_cache)
        await cache.set_value('healthcheck', health_data['timestamp'])

    return web.json_response(health_data)


app = web.Application()
app.on_startup.append(on_startup)
app.router.add_get('/health', healthcheck)


if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=9002)
