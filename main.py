import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List

from aiohttp import web

from vihorki.infrastructure.postgres.on_startup.run_db import init_db_and_tables, engine, Session
from vihorki.infrastructure.redis.redis_tools import redis_conn_context, RedisCache
from vihorki.infrastructure.settings import REDIS_HOST, REDIS_IS_CLUSTER, REDIS_PASSWORD, REDIS_PORT, REDIS_USER
from vihorki.infrastructure.postgres.uow import UnitOfWork
from vihorki.metrics_analyzer.orchestrator import AnalysisOrchestrator
from vihorki.metrics_analyzer.config import load_config
from vihorki.metrics_analyzer.models import MetricsPayload
from vihorki.services.metrics_aggregator import MetricsAggregator
from vihorki.services.llm_response_formatter import create_human_readable_response

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator = None


async def on_startup(app):
    """Initialize database and LLM service on startup"""
    global orchestrator
    
    try:
        await init_db_and_tables()
        logger.info('Successfully setup db')
    except Exception as e:
        logger.error(f'Ошибка инициализации БД: {e}')
        raise
    
    # Initialize LLM orchestrator if credentials are available
    try:
        config = load_config()
        if config.yandex_folder_id and config.yandex_api_key:
            orchestrator = AnalysisOrchestrator(
                metrics_api_url=config.metrics_api_url,
                metrics_api_key=config.metrics_api_key,
                yandex_folder_id=config.yandex_folder_id,
                yandex_api_key=config.yandex_api_key,
                llm_model=config.yandex_llm_model
            )
            logger.info('Successfully initialized LLM orchestrator')
        else:
            logger.warning('LLM orchestrator not initialized: missing Yandex Cloud credentials')
    except Exception as e:
        logger.error(f'Failed to initialize LLM orchestrator: {e}')
        # Don't raise - allow service to start without LLM


async def on_cleanup(app):
    """Cleanup resources on shutdown"""
    global orchestrator
    if orchestrator:
        try:
            await orchestrator.close()
            logger.info('LLM orchestrator closed')
        except Exception as e:
            logger.error(f'Error closing LLM orchestrator: {e}')


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


async def analyze_metrics(request: web.Request) -> web.Response:
    """
    Endpoint for analyzing metrics with LLM
    POST /api/v1/analyze-metrics
    """
    global orchestrator
    
    if not orchestrator:
        return web.json_response(
            {'error': 'LLM service not available. Check Yandex Cloud credentials.'},
            status=503
        )
    
    try:
        payload_dict = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    
    try:
        # Parse payload using Pydantic model
        payload = MetricsPayload(**payload_dict)
        
        # Get optional parameters
        submit_to_api = request.query.get('submit_to_api', 'true').lower() == 'true'
        analyze_with_llm = request.query.get('analyze_with_llm', 'true').lower() == 'true'
        reasoning_effort = request.query.get('reasoning_effort', 'medium')
        
        # Perform analysis
        results = await orchestrator.analyze_and_submit(
            payload=payload,
            submit_to_api=submit_to_api,
            analyze_with_llm=analyze_with_llm,
            reasoning_effort=reasoning_effort
        )
        
        return web.json_response(results)
        
    except Exception as e:
        logger.exception('Error in analyze_metrics handler')
        return web.json_response({'error': str(e)}, status=500)


async def compare_releases(request: web.Request) -> web.Response:
    """
    Endpoint for comparing two releases
    POST /api/v1/compare-releases
    """
    global orchestrator
    
    if not orchestrator:
        return web.json_response(
            {'error': 'LLM service not available. Check Yandex Cloud credentials.'},
            status=503
        )
    
    try:
        payload_dict = await request.json()
        payload = MetricsPayload(**payload_dict)
        
        comparison = await orchestrator.compare_releases(payload)
        return web.json_response(comparison)
        
    except Exception as e:
        logger.exception('Error in compare_releases handler')
        return web.json_response({'error': str(e)}, status=500)


async def llm_health(request: web.Request) -> web.Response:
    """
    Health check for LLM service
    GET /api/v1/llm-health
    """
    global orchestrator
    
    if not orchestrator:
        return web.json_response({
            'status': 'unavailable',
            'message': 'LLM orchestrator not initialized'
        }, status=503)
    
    try:
        health = await orchestrator.health_check()
        status_code = 200 if health['overall_status'] == 'healthy' else 503
        return web.json_response(health, status=status_code)
    except Exception as e:
        logger.exception('Error in llm_health handler')
        return web.json_response({'error': str(e)}, status=500)


async def frontend_analyze(request: web.Request) -> web.Response:
    """
    Frontend-facing endpoint for metrics analysis.
    Fetches data from DB, aggregates it, sends to LLM, and returns human-readable response.
    
    POST /api/v1/frontend-analyze
    
    Request body:
    {
        "period1": {
            "start": "2022-01-20T00:00:00Z",
            "end": "2022-01-25T23:59:59Z",
            "version": "v1.0.0"  // optional
        },
        "period2": {
            "start": "2022-01-26T00:00:00Z",
            "end": "2022-01-31T23:59:59Z",
            "version": "v2.0.0"  // optional
        },
        "project_name": "My Project",  // optional
        "target_urls": ["/home", "/products"],  // optional, focus on specific URLs
        "reasoning_effort": "medium"  // optional: low, medium, high
    }
    
    Response:
    {
        "success": true,
        "timestamp": "...",
        "project": "My Project",
        "releases": ["v1.0.0", "v2.0.0"],
        "summary": "...",
        "analysis": {
            "text": "...",
            "sections": {...},
            "model_info": {...}
        },
        "validation": {...},
        "error": null
    }
    """
    global orchestrator
    
    if not orchestrator:
        return web.json_response(
            {'error': 'LLM service not available. Check Yandex Cloud credentials.'},
            status=503
        )
    
    try:
        payload_dict = await request.json()
    except json.JSONDecodeError:
        return web.json_response({'error': 'Invalid JSON'}, status=400)
    
    # Parse request parameters
    period1 = payload_dict.get('period1', {})
    period2 = payload_dict.get('period2', {})
    
    if not period1 or not period2:
        return web.json_response({
            'error': 'Both period1 and period2 are required with start and end dates'
        }, status=400)
    
    try:
        # Parse period 1
        period1_start = datetime.fromisoformat(period1['start'].replace('Z', '+00:00'))
        period1_end = datetime.fromisoformat(period1['end'].replace('Z', '+00:00'))
        version1 = period1.get('version', 'v1.0.0')
        
        # Parse period 2
        period2_start = datetime.fromisoformat(period2['start'].replace('Z', '+00:00'))
        period2_end = datetime.fromisoformat(period2['end'].replace('Z', '+00:00'))
        version2 = period2.get('version', 'v2.0.0')
    except (KeyError, ValueError) as e:
        return web.json_response({
            'error': f'Invalid date format or missing fields: {str(e)}'
        }, status=400)
    
    project_name = payload_dict.get('project_name', 'Analytics Project')
    target_urls = payload_dict.get('target_urls')
    reasoning_effort = payload_dict.get('reasoning_effort', 'medium')
    
    try:
        # Step 1: Aggregate metrics from database
        logger.info(f"Aggregating metrics for periods: {period1_start} - {period1_end} vs {period2_start} - {period2_end}")
        
        async with Session() as session:
            aggregator = MetricsAggregator(session)
            metrics_payload = await aggregator.aggregate_for_periods(
                period1_start=period1_start,
                period1_end=period1_end,
                period2_start=period2_start,
                period2_end=period2_end,
                version1=version1,
                version2=version2,
                project_name=project_name,
                target_urls=target_urls
            )
        
        logger.info(f"Metrics aggregated: {metrics_payload.releases[0].release_info.total_visits} vs {metrics_payload.releases[1].release_info.total_visits} visits")
        
        # Step 2: Send to LLM for analysis
        logger.info("Sending metrics to LLM for analysis")
        
        analysis_result = await orchestrator.analyze_and_submit(
            payload=metrics_payload,
            submit_to_api=False,  # Don't submit to external API
            analyze_with_llm=True,
            reasoning_effort=reasoning_effort
        )
        
        # Step 3: Format response for frontend (human-readable)
        formatted_response = create_human_readable_response(
            analysis_result,
            include_raw=True
        )
        
        # Add aggregated metrics summary
        formatted_response['metrics_summary'] = {
            'period1': {
                'version': version1,
                'start': period1_start.isoformat(),
                'end': period1_end.isoformat(),
                'total_visits': metrics_payload.releases[0].release_info.total_visits,
                'total_hits': metrics_payload.releases[0].release_info.total_hits,
                'unique_clients': metrics_payload.releases[0].release_info.unique_clients
            },
            'period2': {
                'version': version2,
                'start': period2_start.isoformat(),
                'end': period2_end.isoformat(),
                'total_visits': metrics_payload.releases[1].release_info.total_visits,
                'total_hits': metrics_payload.releases[1].release_info.total_hits,
                'unique_clients': metrics_payload.releases[1].release_info.unique_clients
            }
        }
        
        return web.json_response(formatted_response)
        
    except Exception as e:
        logger.exception('Error in frontend_analyze handler')
        return web.json_response({'error': str(e)}, status=500)


async def get_available_dates(request: web.Request) -> web.Response:
    """
    Get available date range in the database.
    Useful for frontend to show valid date picker bounds.
    
    GET /api/v1/available-dates
    """
    try:
        from sqlalchemy import select, func
        from vihorki.infrastructure.postgres.on_startup.init_tables import VisitTable
        
        async with Session() as session:
            # Get min and max dates
            stmt = select(
                func.min(VisitTable.date_time),
                func.max(VisitTable.date_time),
                func.count(VisitTable.visit_id)
            )
            result = await session.execute(stmt)
            row = result.one()
            
            min_date, max_date, total_visits = row
            
            return web.json_response({
                'min_date': min_date.isoformat() if min_date else None,
                'max_date': max_date.isoformat() if max_date else None,
                'total_visits': total_visits
            })
            
    except Exception as e:
        logger.exception('Error in get_available_dates handler')
        return web.json_response({'error': str(e)}, status=500)


async def get_top_urls(request: web.Request) -> web.Response:
    """
    Get top URLs by visit count.
    Useful for frontend to populate URL filters.
    
    GET /api/v1/top-urls?limit=20
    """
    try:
        from sqlalchemy import select, func
        from vihorki.infrastructure.postgres.on_startup.init_tables import VisitTable
        
        limit = int(request.query.get('limit', '20'))
        
        async with Session() as session:
            # Get top start URLs
            stmt = select(
                VisitTable.start_url,
                func.count(VisitTable.visit_id).label('count')
            ).where(
                VisitTable.start_url.isnot(None)
            ).group_by(
                VisitTable.start_url
            ).order_by(
                func.count(VisitTable.visit_id).desc()
            ).limit(limit)
            
            result = await session.execute(stmt)
            urls = [{'url': row[0], 'visits': row[1]} for row in result.all()]
            
            return web.json_response({'urls': urls})
            
    except Exception as e:
        logger.exception('Error in get_top_urls handler')
        return web.json_response({'error': str(e)}, status=500)


app = web.Application()
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)

# Original endpoints
app.router.add_get('/health', healthcheck)
app.router.add_post('/api/v1/ux-metrics', ux_metrics)

# LLM service endpoints
app.router.add_post('/api/v1/analyze-metrics', analyze_metrics)
app.router.add_post('/api/v1/compare-releases', compare_releases)
app.router.add_get('/api/v1/llm-health', llm_health)

# Frontend-facing endpoints
app.router.add_post('/api/v1/frontend-analyze', frontend_analyze)
app.router.add_get('/api/v1/available-dates', get_available_dates)
app.router.add_get('/api/v1/top-urls', get_top_urls)

if __name__ == '__main__':
    port = int(os.getenv('APP_PORT', 9002))
    logger.info(f'Starting vihorki service on port {port}')
    web.run_app(app, host='0.0.0.0', port=port)
