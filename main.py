import asyncio
import json
import logging
from datetime import datetime, timedelta

from aiohttp import web

from vihorki.infrastructure.postgres.on_startup.run_db import init_db_and_tables, engine
from vihorki.infrastructure.redis.redis_tools import redis_conn_context, RedisCache
from vihorki.infrastructure.settings import REDIS_HOST, REDIS_IS_CLUSTER, REDIS_PASSWORD, REDIS_PORT, REDIS_USER
from vihorki.infrastructure.postgres.uow import UnitOfWork

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


async def ux_metrics(request: web.Request) -> web.Response:
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)

    now = datetime.utcnow()
    time_start_str = payload.get('time_start')
    time_end_str = payload.get('time_end')

    if time_start_str is None:
        time_start = now - timedelta(days=7)
    else:
        try:
            time_start = datetime.fromisoformat(time_start_str.replace('Z', '+00:00'))
        except ValueError:
            return web.json_response({'error': 'Invalid time_start format'}, status=400)

    if time_end_str is None:
        time_end = now
    else:
        try:
            time_end = datetime.fromisoformat(time_end_str.replace('Z', '+00:00'))
        except ValueError:
            return web.json_response({'error': 'Invalid time_end format'}, status=400)

    is_new_user = payload.get('is_new_user')
    device = payload.get('device')

    if is_new_user is None or device is None:
        return web.json_response({'error': "'is_new_user' (bool) and 'device' ('1' or '2') are required"}, status=400)

    if device not in ('1', '2'):
        return web.json_response({'error': "device must be '1' (desktop) or '2' (mobile)"}, status=400)

    operating_system = payload.get('operating_system')
    is_landscape = payload.get('is_landscape')
    region_city = payload.get('region_city')
    try:
        async with UnitOfWork(engine) as uow:
            all_metrics = await uow.metric_repo.get_by_timedelta(time_start, time_end)
            filtered = []
            for m in all_metrics:
                if m.visit.is_new_user != is_new_user:
                    continue
                if str(m.visit.device_category) != device:
                    continue
                if operating_system and m.visit.operating_system != operating_system:
                    continue
                if is_landscape is not None:
                    expected = 'landscape' if is_landscape == '1' else 'portrait'
                    if m.visit.screen_orientation_name != expected:
                        continue
                if region_city and m.visit.region_city != region_city:
                    continue
                filtered.append(m)

            durations = [m.visit.visit_duration for m in filtered if m.visit.visit_duration is not None]

            if not durations:
                return web.json_response(
                    {
                        'count': 0,
                        'avg_duration_sec': None,
                        'median_duration_sec': None,
                        'min_duration_sec': None,
                        'max_duration_sec': None,
                        'message': 'No matching visits',
                    }
                )

            durations.sort()
            n = len(durations)
            avg = sum(durations) / n
            median = durations[n // 2] if n % 2 == 1 else (durations[n // 2 - 1] + durations[n // 2]) / 2

            result = {
                'count': n,
                'avg_duration_sec': round(avg, 2),
                'median_duration_sec': round(median, 2),
                'min_duration_sec': min(durations),
                'max_duration_sec': max(durations),
                'time_range': {'start': time_start.isoformat(), 'end': time_end.isoformat()},
                'filters_applied': {
                    'is_new_user': is_new_user,
                    'device': 'desktop' if device == '1' else 'mobile',
                    'operating_system': operating_system,
                    'is_landscape': is_landscape,
                    'region_city': region_city,
                },
            }

            return web.json_response(result)

    except Exception:
        logger.exception('Error in ux_metrics handler')
        return web.json_response({'error': 'Internal server error'}, status=500)


app = web.Application()
app.on_startup.append(on_startup)
app.router.add_get('/health', healthcheck)
app.router.add_post('/api/v1/ux-metrics', ux_metrics)

if __name__ == '__main__':
    web.run_app(app, host='0.0.0.0', port=9002)
