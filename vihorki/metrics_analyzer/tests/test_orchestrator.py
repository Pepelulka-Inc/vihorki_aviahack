"""
Tests for AnalysisOrchestrator
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from vihorki.metrics_analyzer.orchestrator import AnalysisOrchestrator
from vihorki.metrics_analyzer.models import (
    MetricsPayload, Metadata, Release, ReleaseInfo, DataPeriod,
    AggregateMetrics, VisitsMetrics, PageViewsMetrics,
    SessionDistribution, DeviceBreakdown, TrafficSources,
    GeographicDistribution, NavigationPatterns, ReverseNavigation,
    FunnelMetrics, SessionComplexityMetrics, HighInteractionSessions,
    URLRevisitPatterns
)


def create_minimal_release(version: str, total_visits: int = 1000) -> Release:
    """Helper to create minimal release for testing"""
    return Release(
        release_info=ReleaseInfo(
            version=version,
            data_period=DataPeriod(
                start=datetime(2025, 1, 1),
                end=datetime(2025, 1, 7)
            ),
            total_visits=total_visits,
            total_hits=5000,
            unique_clients=800
        ),
        aggregate_metrics=AggregateMetrics(
            visits=VisitsMetrics(
                total_count=total_visits,
                new_users=600,
                returning_users=400,
                avg_page_views=5.0,
                median_page_views=4,
                avg_duration_sec=120,
                median_duration_sec=100,
                total_duration_sec=120000
            ),
            page_views=PageViewsMetrics(
                total_count=5000,
                unique_urls=50
            )
        ),
        session_distribution=SessionDistribution(by_page_views=[], by_duration_sec=[]),
        device_breakdown=DeviceBreakdown(by_category=[], by_os=[], by_browser=[], by_screen_orientation=[]),
        traffic_sources=TrafficSources(by_search_engine=[]),
        geographic_distribution=GeographicDistribution(top_cities=[]),
        page_metrics=[],
        navigation_patterns=NavigationPatterns(
            reverse_navigation=ReverseNavigation(
                visits_with_reverse_nav=100,
                percentage=10.0,
                total_reverse_transitions=150
            ),
            common_transitions=[],
            loop_patterns=[]
        ),
        funnel_metrics=FunnelMetrics(application_funnel=[]),
        session_complexity_metrics=SessionComplexityMetrics(
            high_interaction_sessions=HighInteractionSessions(
                sessions_with_10plus_pages=50,
                percentage=5.0,
                avg_pages=12.0,
                avg_duration_sec=300,
                avg_unique_urls=10.0
            ),
            url_revisit_patterns=URLRevisitPatterns(
                sessions_with_url_revisits=200,
                percentage=20.0,
                avg_revisits_per_session=2.5,
                avg_unique_urls_revisited=3.0
            )
        )
    )


@pytest.fixture
def sample_payload():
    """Create sample metrics payload for testing"""
    metadata = Metadata(
        project_name="Test Project",
        generated_at=datetime.now(),
        data_source="test_db"
    )
    
    return MetricsPayload(
        metadata=metadata,
        releases=[
            create_minimal_release("1.0.0", 1000),
            create_minimal_release("1.1.0", 1200)
        ]
    )


class TestAnalysisOrchestrator:
    """Tests for AnalysisOrchestrator"""
    
    def test_init(self):
        """Test orchestrator initialization"""
        orchestrator = AnalysisOrchestrator(
            metrics_api_url="http://test.com",
            metrics_api_key="test_key",
            yandex_folder_id="test_folder",
            yandex_api_key="test_api_key"
        )
        assert orchestrator.api_client is not None
        assert orchestrator.llm_client is not None
    
    @pytest.mark.asyncio
    async def test_analyze_and_submit_validation_failed(self, sample_payload):
        """Test workflow with validation failure"""
        orchestrator = AnalysisOrchestrator(
            metrics_api_url="http://test.com",
            yandex_folder_id="test",
            yandex_api_key="test"
        )
        
        sample_payload.releases = [sample_payload.releases[0]]
        
        result = await orchestrator.analyze_and_submit(sample_payload)
        
        assert result["validation"]["status"] == "failed"
        assert "api_submission" not in result or result["api_submission"]["status"] == "skipped"
        
        await orchestrator.close()
    
    @pytest.mark.asyncio
    async def test_analyze_and_submit_success(self, sample_payload):
        """Test successful workflow"""
        orchestrator = AnalysisOrchestrator(
            metrics_api_url="http://test.com",
            yandex_folder_id="test",
            yandex_api_key="test"
        )
        
        with patch.object(orchestrator.api_client, 'send_metrics', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = {"status": "success", "status_code": 200}
            
            with patch.object(orchestrator.llm_client, 'analyze_metrics', new_callable=AsyncMock) as mock_llm:
                mock_llm.return_value = {
                    "status": "success",
                    "response_id": "test_id",
                    "analysis": "Test analysis"
                }
                
                result = await orchestrator.analyze_and_submit(sample_payload)
                
                assert result["validation"]["status"] == "passed"
                assert result["api_submission"]["status"] == "success"
                assert result["llm_analysis"]["status"] == "success"
        
        await orchestrator.close()
    
    @pytest.mark.asyncio
    async def test_compare_releases(self, sample_payload):
        """Test release comparison"""
        orchestrator = AnalysisOrchestrator(
            metrics_api_url="http://test.com",
            yandex_folder_id="test",
            yandex_api_key="test"
        )
        
        result = await orchestrator.compare_releases(sample_payload)
        
        assert result["status"] == "success"
        assert "metrics_comparison" in result
        assert "visits" in result["metrics_comparison"]
        assert result["metrics_comparison"]["visits"]["total_change"] == 200
        
        await orchestrator.close()
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check"""
        orchestrator = AnalysisOrchestrator(
            metrics_api_url="http://test.com",
            yandex_folder_id="test",
            yandex_api_key="test"
        )
        
        with patch.object(orchestrator.api_client, 'health_check', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True
            
            result = await orchestrator.health_check()
            
            assert "services" in result
            assert "metrics_api" in result["services"]
            assert "llm_client" in result["services"]
        
        await orchestrator.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])