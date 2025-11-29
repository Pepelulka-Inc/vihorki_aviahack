"""
Example usage of the Metrics Analyzer Service
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from .models import (
    MetricsPayload, Metadata, Release, ReleaseInfo, DataPeriod,
    AggregateMetrics, VisitsMetrics, PageViewsMetrics,
    SessionDistribution, DistributionBucket,
    DeviceBreakdown, DeviceCategoryMetric, SegmentMetric,
    TrafficSources, GeographicDistribution,
    PageMetric, NavigationPatterns, ReverseNavigation,
    PageTransition, LoopPattern, FunnelMetrics, FunnelStep,
    SessionComplexityMetrics, HighInteractionSessions, URLRevisitPatterns
)
from .orchestrator import AnalysisOrchestrator
from .config import load_config


def create_sample_payload() -> MetricsPayload:
    """Create a sample metrics payload for testing"""
    
    metadata = Metadata(
        project_name="Sample UX Project",
        generated_at=datetime.utcnow(),
        data_source="analytics_database"
    )
    
    def create_release(version: str, days_ago: int, multiplier: float = 1.0) -> Release:
        end_date = datetime.utcnow() - timedelta(days=days_ago)
        start_date = end_date - timedelta(days=7)
        
        return Release(
            release_info=ReleaseInfo(
                version=version,
                data_period=DataPeriod(start=start_date, end=end_date),
                total_visits=int(10000 * multiplier),
                total_hits=int(50000 * multiplier),
                unique_clients=int(8000 * multiplier)
            ),
            aggregate_metrics=AggregateMetrics(
                visits=VisitsMetrics(
                    total_count=int(10000 * multiplier),
                    new_users=int(3000 * multiplier),
                    returning_users=int(7000 * multiplier),
                    avg_page_views=5.2 * multiplier,
                    median_page_views=int(4 * multiplier),
                    avg_duration_sec=int(180 * multiplier),
                    median_duration_sec=int(120 * multiplier),
                    total_duration_sec=int(1800000 * multiplier)
                ),
                page_views=PageViewsMetrics(
                    total_count=int(50000 * multiplier),
                    unique_urls=int(250 * multiplier)
                )
            ),
            session_distribution=SessionDistribution(
                by_page_views=[
                    DistributionBucket(range_min=1, range_max=1, count=int(2000 * multiplier), percentage=20.0),
                    DistributionBucket(range_min=2, range_max=5, count=int(5000 * multiplier), percentage=50.0),
                    DistributionBucket(range_min=6, range_max=10, count=int(2000 * multiplier), percentage=20.0),
                    DistributionBucket(range_min=11, range_max=None, count=int(1000 * multiplier), percentage=10.0)
                ],
                by_duration_sec=[
                    DistributionBucket(range_min=0, range_max=30, count=int(1000 * multiplier), percentage=10.0),
                    DistributionBucket(range_min=31, range_max=120, count=int(4000 * multiplier), percentage=40.0),
                    DistributionBucket(range_min=121, range_max=300, count=int(3000 * multiplier), percentage=30.0),
                    DistributionBucket(range_min=301, range_max=None, count=int(2000 * multiplier), percentage=20.0)
                ]
            ),
            device_breakdown=DeviceBreakdown(
                by_category=[
                    DeviceCategoryMetric(
                        device_category=1,
                        segment_value="Desktop",
                        visits=int(6000 * multiplier),
                        percentage=60.0,
                        avg_page_views=5.5,
                        avg_duration_sec=200,
                        single_page_visits=int(1000 * multiplier)
                    ),
                    DeviceCategoryMetric(
                        device_category=2,
                        segment_value="Mobile",
                        visits=int(4000 * multiplier),
                        percentage=40.0,
                        avg_page_views=4.8,
                        avg_duration_sec=150,
                        single_page_visits=int(1200 * multiplier)
                    )
                ],
                by_os=[
                    SegmentMetric(
                        segment_value="Windows",
                        visits=int(4000 * multiplier),
                        percentage=40.0,
                        avg_page_views=5.3,
                        avg_duration_sec=190,
                        single_page_visits=int(700 * multiplier)
                    ),
                    SegmentMetric(
                        segment_value="iOS",
                        visits=int(2500 * multiplier),
                        percentage=25.0,
                        avg_page_views=4.9,
                        avg_duration_sec=160,
                        single_page_visits=int(600 * multiplier)
                    ),
                    SegmentMetric(
                        segment_value="Android",
                        visits=int(2000 * multiplier),
                        percentage=20.0,
                        avg_page_views=4.7,
                        avg_duration_sec=140,
                        single_page_visits=int(650 * multiplier)
                    )
                ],
                by_browser=[
                    SegmentMetric(
                        segment_value="Chrome",
                        visits=int(5000 * multiplier),
                        percentage=50.0,
                        avg_page_views=5.1,
                        avg_duration_sec=175,
                        single_page_visits=int(1000 * multiplier)
                    ),
                    SegmentMetric(
                        segment_value="Safari",
                        visits=int(3000 * multiplier),
                        percentage=30.0,
                        avg_page_views=5.0,
                        avg_duration_sec=170,
                        single_page_visits=int(700 * multiplier)
                    )
                ],
                by_screen_orientation=[
                    SegmentMetric(
                        segment_value="landscape",
                        visits=int(7000 * multiplier),
                        percentage=70.0,
                        avg_page_views=5.3,
                        avg_duration_sec=185,
                        single_page_visits=int(1300 * multiplier)
                    ),
                    SegmentMetric(
                        segment_value="portrait",
                        visits=int(3000 * multiplier),
                        percentage=30.0,
                        avg_page_views=4.9,
                        avg_duration_sec=165,
                        single_page_visits=int(900 * multiplier)
                    )
                ]
            ),
            traffic_sources=TrafficSources(
                by_search_engine=[
                    SegmentMetric(
                        segment_value="google",
                        visits=int(5000 * multiplier),
                        percentage=50.0,
                        avg_page_views=5.2,
                        avg_duration_sec=180,
                        single_page_visits=int(1000 * multiplier)
                    ),
                    SegmentMetric(
                        segment_value="yandex",
                        visits=int(3000 * multiplier),
                        percentage=30.0,
                        avg_page_views=5.0,
                        avg_duration_sec=175,
                        single_page_visits=int(700 * multiplier)
                    )
                ]
            ),
            geographic_distribution=GeographicDistribution(
                top_cities=[
                    SegmentMetric(
                        segment_value="Moscow",
                        visits=int(3000 * multiplier),
                        percentage=30.0,
                        avg_page_views=5.5,
                        avg_duration_sec=200,
                        single_page_visits=int(500 * multiplier)
                    ),
                    SegmentMetric(
                        segment_value="Saint Petersburg",
                        visits=int(2000 * multiplier),
                        percentage=20.0,
                        avg_page_views=5.2,
                        avg_duration_sec=185,
                        single_page_visits=int(400 * multiplier)
                    )
                ]
            ),
            page_metrics=[
                PageMetric(
                    url="/home",
                    title="Home Page",
                    visits_as_entry=int(5000 * multiplier),
                    visits_as_exit=int(2000 * multiplier),
                    total_hits=int(8000 * multiplier),
                    unique_visitors=int(4500 * multiplier),
                    visits_with_single_page=int(1000 * multiplier),
                    subsequent_page_diversity=15
                ),
                PageMetric(
                    url="/products",
                    title="Products",
                    visits_as_entry=int(2000 * multiplier),
                    visits_as_exit=int(3000 * multiplier),
                    total_hits=int(6000 * multiplier),
                    unique_visitors=int(3500 * multiplier),
                    visits_with_single_page=int(500 * multiplier),
                    subsequent_page_diversity=10
                )
            ],
            navigation_patterns=NavigationPatterns(
                reverse_navigation=ReverseNavigation(
                    visits_with_reverse_nav=int(2000 * multiplier),
                    percentage=20.0 * multiplier,
                    total_reverse_transitions=int(3500 * multiplier)
                ),
                common_transitions=[
                    PageTransition(
                        from_url="/home",
                        to_url="/products",
                        transition_count=int(3000 * multiplier)
                    ),
                    PageTransition(
                        from_url="/products",
                        to_url="/product-detail",
                        transition_count=int(2000 * multiplier)
                    )
                ],
                loop_patterns=[
                    LoopPattern(
                        sequence=["/products", "/product-detail", "/products"],
                        occurrences=int(500 * multiplier)
                    )
                ]
            ),
            funnel_metrics=FunnelMetrics(
                application_funnel=[
                    FunnelStep(
                        step=1,
                        url="/home",
                        visits_entered=int(10000 * multiplier),
                        visits_completed=int(7000 * multiplier)
                    ),
                    FunnelStep(
                        step=2,
                        url="/products",
                        visits_entered=int(7000 * multiplier),
                        visits_completed=int(4000 * multiplier)
                    ),
                    FunnelStep(
                        step=3,
                        url="/checkout",
                        visits_entered=int(4000 * multiplier),
                        visits_completed=int(2000 * multiplier)
                    )
                ]
            ),
            session_complexity_metrics=SessionComplexityMetrics(
                high_interaction_sessions=HighInteractionSessions(
                    sessions_with_10plus_pages=int(1000 * multiplier),
                    percentage=10.0 * multiplier,
                    avg_pages=15.5,
                    avg_duration_sec=450,
                    avg_unique_urls=12.3
                ),
                url_revisit_patterns=URLRevisitPatterns(
                    sessions_with_url_revisits=int(2500 * multiplier),
                    percentage=25.0 * multiplier,
                    avg_revisits_per_session=2.8,
                    avg_unique_urls_revisited=1.9
                )
            )
        )
    
    release_old = create_release("v1.0.0", days_ago=14, multiplier=1.0)
    
    release_new = create_release("v1.1.0", days_ago=0, multiplier=1.15)
    
    return MetricsPayload(
        metadata=metadata,
        releases=[release_old, release_new]
    )


async def example_full_analysis():
    """Example: Full analysis workflow"""
    print("=" * 80)
    print("EXAMPLE: Full Analysis Workflow")
    print("=" * 80)
    
    config = load_config()
    
    payload = create_sample_payload()
    print(f"\n✓ Created sample payload for project: {payload.metadata.project_name}")
    print(f"  Comparing releases: {payload.releases[0].release_info.version} vs {payload.releases[1].release_info.version}")
    
    async with AnalysisOrchestrator(
        metrics_api_url=config.metrics_api_url,
        metrics_api_key=config.metrics_api_key,
        yandex_folder_id=config.yandex_folder_id,
        yandex_api_key=config.yandex_api_key,
        llm_model=config.yandex_llm_model
    ) as orchestrator:
        
        print("\n📊 Starting analysis...")
        results = await orchestrator.analyze_and_submit(
            payload=payload,
            submit_to_api=config.enable_api_submission,
            analyze_with_llm=config.enable_llm_analysis,
            focus_areas=[
                "Блуждающие сессии",
                "Обратная навигация",
                "Петли в навигации",
                "Конверсия в воронках"
            ]
        )
        
        print("\n" + "=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        
        print(f"\n✓ Validation: {results['validation']['status']}")
        
        if 'api_submission' in results:
            print(f"✓ API Submission: {results['api_submission']['status']}")
        
        if 'llm_analysis' in results and results['llm_analysis']['status'] == 'success':
            print(f"\n📝 LLM Analysis:")
            print("-" * 80)
            print(results['llm_analysis']['analysis'])
            print("-" * 80)
            
            print("\n🎯 Getting detailed recommendations...")
            recommendations = await orchestrator.get_detailed_recommendations(
                results,
                priority="high"
            )
            
            if recommendations['status'] == 'success':
                print("\n📋 Recommendations:")
                print("-" * 80)
                print(recommendations['analysis'])
                print("-" * 80)


async def example_comparison_only():
    """Example: Quick comparison without LLM"""
    print("=" * 80)
    print("EXAMPLE: Quick Comparison")
    print("=" * 80)
    
    config = load_config()
    payload = create_sample_payload()
    
    async with AnalysisOrchestrator(
        metrics_api_url=config.metrics_api_url,
        yandex_folder_id=config.yandex_folder_id,
        yandex_api_key=config.yandex_api_key
    ) as orchestrator:
        
        comparison = await orchestrator.compare_releases(payload)
        
        print(f"\n📊 Comparison Results:")
        print(f"  Releases: {comparison['releases']['old']} → {comparison['releases']['new']}")
        print(f"\n  Metrics Changes:")
        print(f"    Total visits: {comparison['metrics_comparison']['visits']['total_change']:+d} "
              f"({comparison['metrics_comparison']['visits']['total_change_pct']:+.1f}%)")
        print(f"    Avg duration: {comparison['metrics_comparison']['visits']['avg_duration_change']:+d} sec")
        print(f"    Avg page views: {comparison['metrics_comparison']['visits']['avg_page_views_change']:+.2f}")
        print(f"    Reverse navigation: {comparison['metrics_comparison']['navigation']['reverse_nav_change_pct']:+.1f}%")
        print(f"    Loop patterns: {comparison['metrics_comparison']['navigation']['loop_patterns_change']:+d}")
        
        print(f"\n  ⚠️  Concern Level: {comparison['concern_level'].upper()}")
        if comparison['concerns']:
            print(f"  Concerns:")
            for concern in comparison['concerns']:
                print(f"    - {concern}")


async def example_health_check():
    """Example: Health check"""
    print("=" * 80)
    print("EXAMPLE: Health Check")
    print("=" * 80)
    
    config = load_config()
    
    async with AnalysisOrchestrator(
        metrics_api_url=config.metrics_api_url,
        yandex_folder_id=config.yandex_folder_id,
        yandex_api_key=config.yandex_api_key
    ) as orchestrator:
        
        health = await orchestrator.health_check()
        
        print(f"\n🏥 Health Status: {health['overall_status'].upper()}")
        print(f"  Timestamp: {health['timestamp']}")
        print(f"\n  Services:")
        for service, status in health['services'].items():
            print(f"    {service}: {status['status']}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("METRICS ANALYZER SERVICE - EXAMPLES")
    print("=" * 80)
    
    asyncio.run(example_full_analysis())
    
    print("\n\n")
    
    asyncio.run(example_comparison_only())
    
    print("\n\n")
    
    asyncio.run(example_health_check())