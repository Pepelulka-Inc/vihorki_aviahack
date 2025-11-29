import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
import aiohttp

from aiohttp import web

from vihorki.infrastructure.postgres.on_startup.run_db import init_db_and_tables, engine
from vihorki.infrastructure.redis.redis_tools import redis_conn_context, RedisCache
from vihorki.infrastructure.settings import REDIS_HOST, REDIS_IS_CLUSTER, REDIS_PASSWORD, REDIS_PORT, REDIS_USER
from vihorki.infrastructure.postgres.uow import UnitOfWork
from vihorki.metrics_analyzer.orchestrator import AnalysisOrchestrator
from vihorki.metrics_analyzer.config import load_config
from vihorki.metrics_analyzer.models import MetricsPayload

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


async def send_auto_request():
    """
    Automatically send the curl request after application starts
    """
    # Wait a bit for the server to be ready
    await asyncio.sleep(2)
    
    url = "http://localhost:9002/api/v1/analyze-metrics?submit_to_api=false"
    
    payload = {
        "metadata": {
            "project_name": "Test Project",
            "generated_at": "2024-01-31T12:00:00Z",
            "data_source": "analytics_db"
        },
        "releases": [
            {
                "release_info": {
                    "version": "v1.0.0",
                    "data_period": {
                        "start": "2024-01-01T00:00:00Z",
                        "end": "2024-01-07T23:59:59Z"
                    },
                    "total_visits": 10000,
                    "total_hits": 50000,
                    "unique_clients": 8000
                },
                "aggregate_metrics": {
                    "visits": {
                        "total_count": 10000,
                        "new_users": 3000,
                        "returning_users": 7000,
                        "avg_page_views": 5.2,
                        "median_page_views": 4,
                        "avg_duration_sec": 180,
                        "median_duration_sec": 120,
                        "total_duration_sec": 1800000
                    },
                    "page_views": {
                        "total_count": 50000,
                        "unique_urls": 250
                    }
                },
                "session_distribution": {
                    "by_page_views": [
                        {"range_min": 1, "range_max": 1, "count": 2000, "percentage": 20.0},
                        {"range_min": 2, "range_max": 5, "count": 5000, "percentage": 50.0},
                        {"range_min": 6, "range_max": 10, "count": 2000, "percentage": 20.0},
                        {"range_min": 11, "range_max": None, "count": 1000, "percentage": 10.0}
                    ],
                    "by_duration_sec": [
                        {"range_min": 0, "range_max": 30, "count": 1000, "percentage": 10.0},
                        {"range_min": 31, "range_max": 120, "count": 4000, "percentage": 40.0},
                        {"range_min": 121, "range_max": 300, "count": 3000, "percentage": 30.0},
                        {"range_min": 301, "range_max": None, "count": 2000, "percentage": 20.0}
                    ]
                },
                "device_breakdown": {
                    "by_category": [
                        {"device_category": 1, "segment_value": "Desktop", "visits": 6000, "percentage": 60.0, "avg_page_views": 5.5, "avg_duration_sec": 200, "single_page_visits": 1000}
                    ],
                    "by_os": [
                        {"segment_value": "Windows", "visits": 4000, "percentage": 40.0, "avg_page_views": 5.3, "avg_duration_sec": 190, "single_page_visits": 700}
                    ],
                    "by_browser": [
                        {"segment_value": "Chrome", "visits": 5000, "percentage": 50.0, "avg_page_views": 5.1, "avg_duration_sec": 175, "single_page_visits": 1000}
                    ],
                    "by_screen_orientation": [
                        {"segment_value": "landscape", "visits": 7000, "percentage": 70.0, "avg_page_views": 5.3, "avg_duration_sec": 185, "single_page_visits": 1300}
                    ]
                },
                "traffic_sources": {
                    "by_search_engine": [
                        {"segment_value": "google", "visits": 5000, "percentage": 50.0, "avg_page_views": 5.2, "avg_duration_sec": 180, "single_page_visits": 1000}
                    ]
                },
                "geographic_distribution": {
                    "top_cities": [
                        {"segment_value": "Moscow", "visits": 3000, "percentage": 30.0, "avg_page_views": 5.5, "avg_duration_sec": 200, "single_page_visits": 500}
                    ]
                },
                "page_metrics": [
                    {"url": "/home", "title": "Home", "visits_as_entry": 5000, "visits_as_exit": 2000, "total_hits": 8000, "unique_visitors": 4500, "visits_with_single_page": 1000, "subsequent_page_diversity": 15}
                ],
                "navigation_patterns": {
                    "reverse_navigation": {"visits_with_reverse_nav": 2000, "percentage": 20.0, "total_reverse_transitions": 3500},
                    "common_transitions": [
                        {"from_url": "/home", "to_url": "/products", "transition_count": 3000}
                    ],
                    "loop_patterns": [
                        {"sequence": ["/products", "/detail", "/products"], "occurrences": 500}
                    ]
                },
                "funnel_metrics": {
                    "application_funnel": [
                        {"step": 1, "url": "/home", "visits_entered": 10000, "visits_completed": 7000}
                    ]
                },
                "session_complexity_metrics": {
                    "high_interaction_sessions": {"sessions_with_10plus_pages": 1000, "percentage": 10.0, "avg_pages": 15.5, "avg_duration_sec": 450, "avg_unique_urls": 12.3},
                    "url_revisit_patterns": {"sessions_with_url_revisits": 2500, "percentage": 25.0, "avg_revisits_per_session": 2.8, "avg_unique_urls_revisited": 1.9}
                }
            },
            {
                "release_info": {
                    "version": "v1.1.0",
                    "data_period": {
                        "start": "2024-01-24T00:00:00Z",
                        "end": "2024-01-31T23:59:59Z"
                    },
                    "total_visits": 11500,
                    "total_hits": 57500,
                    "unique_clients": 9200
                },
                "aggregate_metrics": {
                    "visits": {
                        "total_count": 11500,
                        "new_users": 3450,
                        "returning_users": 8050,
                        "avg_page_views": 5.98,
                        "median_page_views": 5,
                        "avg_duration_sec": 207,
                        "median_duration_sec": 138,
                        "total_duration_sec": 2070000
                    },
                    "page_views": {
                        "total_count": 57500,
                        "unique_urls": 288
                    }
                },
                "session_distribution": {
                    "by_page_views": [
                        {"range_min": 1, "range_max": 1, "count": 1800, "percentage": 15.7},
                        {"range_min": 2, "range_max": 5, "count": 5500, "percentage": 47.8},
                        {"range_min": 6, "range_max": 10, "count": 2700, "percentage": 23.5},
                        {"range_min": 11, "range_max": None, "count": 1500, "percentage": 13.0}
                    ],
                    "by_duration_sec": [
                        {"range_min": 0, "range_max": 30, "count": 900, "percentage": 7.8},
                        {"range_min": 31, "range_max": 120, "count": 4200, "percentage": 36.5},
                        {"range_min": 121, "range_max": 300, "count": 3800, "percentage": 33.0},
                        {"range_min": 301, "range_max": None, "count": 2600, "percentage": 22.6}
                    ]
                },
                "device_breakdown": {
                    "by_category": [
                        {"device_category": 1, "segment_value": "Desktop", "visits": 6900, "percentage": 60.0, "avg_page_views": 6.3, "avg_duration_sec": 230, "single_page_visits": 900}
                    ],
                    "by_os": [
                        {"segment_value": "Windows", "visits": 4600, "percentage": 40.0, "avg_page_views": 6.1, "avg_duration_sec": 219, "single_page_visits": 600}
                    ],
                    "by_browser": [
                        {"segment_value": "Chrome", "visits": 5750, "percentage": 50.0, "avg_page_views": 5.9, "avg_duration_sec": 201, "single_page_visits": 950}
                    ],
                    "by_screen_orientation": [
                        {"segment_value": "landscape", "visits": 8050, "percentage": 70.0, "avg_page_views": 6.1, "avg_duration_sec": 213, "single_page_visits": 1200}
                    ]
                },
                "traffic_sources": {
                    "by_search_engine": [
                        {"segment_value": "google", "visits": 5750, "percentage": 50.0, "avg_page_views": 5.98, "avg_duration_sec": 207, "single_page_visits": 950}
                    ]
                },
                "geographic_distribution": {
                    "top_cities": [
                        {"segment_value": "Moscow", "visits": 3450, "percentage": 30.0, "avg_page_views": 6.3, "avg_duration_sec": 230, "single_page_visits": 450}
                    ]
                },
                "page_metrics": [
                    {"url": "/home", "title": "Home", "visits_as_entry": 5750, "visits_as_exit": 2100, "total_hits": 9200, "unique_visitors": 5175, "visits_with_single_page": 900, "subsequent_page_diversity": 17}
                ],
                "navigation_patterns": {
                    "reverse_navigation": {"visits_with_reverse_nav": 2300, "percentage": 20.0, "total_reverse_transitions": 4025},
                    "common_transitions": [
                        {"from_url": "/home", "to_url": "/products", "transition_count": 3450}
                    ],
                    "loop_patterns": [
                        {"sequence": ["/products", "/detail", "/products"], "occurrences": 575}
                    ]
                },
                "funnel_metrics": {
                    "application_funnel": [
                        {"step": 1, "url": "/home", "visits_entered": 11500, "visits_completed": 8050}
                    ]
                },
                "session_complexity_metrics": {
                    "high_interaction_sessions": {"sessions_with_10plus_pages": 1150, "percentage": 10.0, "avg_pages": 17.8, "avg_duration_sec": 518, "avg_unique_urls": 14.1},
                    "url_revisit_patterns": {"sessions_with_url_revisits": 2875, "percentage": 25.0, "avg_revisits_per_session": 3.2, "avg_unique_urls_revisited": 2.2}
                }
            }
        ]
    }

    try:
        async with aiohttp.ClientSession() as session:
            logger.info("Sending automatic request to analyze-metrics endpoint...")
            async with session.post(url, json=payload, headers={"Content-Type": "application/json"}) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response: {response_text}")
                
                # Print the response in a formatted way
                try:
                    response_json = json.loads(response_text)
                    print("\n" + "="*50)
                    print("AUTO-REQUEST RESULT:")
                    print("="*50)
                    print(json.dumps(response_json, indent=2, ensure_ascii=False))
                    print("="*50)
                except json.JSONDecodeError:
                    print("\n" + "="*50)
                    print("AUTO-REQUEST RESULT:")
                    print("="*50)
                    print(response_text)
                    print("="*50)
                
    except Exception as e:
        logger.error(f"Error sending auto-request: {e}")


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

if __name__ == '__main__':
    port = int(os.getenv('APP_PORT', 9002))
    logger.info(f'Starting vihorki service on port {port}')
    
    # Create the event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start the web application
    runner = web.AppRunner(app)
    loop.run_until_complete(runner.setup())
    site = web.TCPSite(runner, '0.0.0.0', port)
    loop.run_until_complete(site.start())
    
    logger.info(f'Server started at http://0.0.0.0:{port}')
    
    # Schedule the auto-request to run after the server starts
    loop.create_task(send_auto_request())
    
    try:
        # Run forever
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        loop.run_until_complete(runner.cleanup())
        loop.close()