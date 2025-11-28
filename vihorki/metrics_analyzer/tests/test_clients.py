"""
Tests for API and LLM clients
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from vihorki.metrics_analyzer.clients.api import APIClient
from vihorki.metrics_analyzer.clients.llm import LLMClient
from vihorki.metrics_analyzer.models import (
    MetricsPayload, Metadata, Release, ReleaseInfo, DataPeriod,
    AggregateMetrics, VisitsMetrics, PageViewsMetrics,
    SessionDistribution, DeviceBreakdown, TrafficSources,
    GeographicDistribution, NavigationPatterns, ReverseNavigation,
    FunnelMetrics, SessionComplexityMetrics, HighInteractionSessions,
    URLRevisitPatterns
)


def create_minimal_release(version: str) -> Release:
    """Helper to create minimal release for testing"""
    return Release(
        release_info=ReleaseInfo(
            version=version,
            data_period=DataPeriod(
                start=datetime(2025, 1, 1),
                end=datetime(2025, 1, 7)
            ),
            total_visits=1000,
            total_hits=5000,
            unique_clients=800
        ),
        aggregate_metrics=AggregateMetrics(
            visits=VisitsMetrics(
                total_count=1000,
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
            create_minimal_release("1.0.0"),
            create_minimal_release("1.1.0")
        ]
    )


class TestAPIClient:
    """Tests for APIClient"""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """Test client initialization"""
        client = APIClient(base_url="http://test.com", api_key="test_key")
        assert client.base_url == "http://test.com"
        assert client.api_key == "test_key"
        await client.close()
    
    @pytest.mark.asyncio
    async def test_validate_payload_success(self, sample_payload):
        """Test successful payload validation"""
        client = APIClient(base_url="http://test.com")
        is_valid, error = client.validate_payload(sample_payload)
        assert is_valid is True
        assert error is None
        await client.close()
    
    @pytest.mark.asyncio
    async def test_validate_payload_wrong_releases_count(self, sample_payload):
        """Test validation fails with wrong number of releases"""
        client = APIClient(base_url="http://test.com")
        sample_payload.releases = [sample_payload.releases[0]]
        is_valid, error = client.validate_payload(sample_payload)
        assert is_valid is False
        assert "exactly 2 releases" in error.lower()
        await client.close()
    
    @pytest.mark.asyncio
    async def test_send_metrics_success(self, sample_payload):
        """Test successful metrics submission"""
        client = APIClient(base_url="http://test.com")
        
        with patch.object(client._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b'{"status": "ok"}'
            mock_response.json.return_value = {"status": "ok"}
            mock_post.return_value = mock_response
            
            result = await client.send_metrics(sample_payload)
            
            assert result["status"] == "success"
            assert result["status_code"] == 200
            mock_post.assert_called_once()
        
        await client.close()


class TestLLMClient:
    """Tests for LLMClient"""
    
    def test_init_with_credentials(self):
        """Test client initialization with credentials"""
        client = LLMClient(
            folder_id="test_folder",
            api_key="test_key",
            model="test_model"
        )
        assert client.folder_id == "test_folder"
        assert client.api_key == "test_key"
        assert "test_model" in client.model
    
    def test_init_without_credentials(self):
        """Test client initialization fails without credentials"""
        with pytest.raises(ValueError, match="folder_id and api_key must be provided"):
            LLMClient()
    
    @pytest.mark.asyncio
    async def test_analyze_metrics_wrong_releases_count(self, sample_payload):
        """Test analysis fails with wrong number of releases"""
        client = LLMClient(folder_id="test", api_key="test")
        sample_payload.releases = [sample_payload.releases[0]]
        
        with pytest.raises(ValueError, match="exactly 2 releases"):
            await client.analyze_metrics(sample_payload)
    
    @pytest.mark.asyncio
    async def test_analyze_metrics_success(self, sample_payload):
        """Test successful metrics analysis"""
        client = LLMClient(folder_id="test", api_key="test")
        
        with patch.object(client.client.responses, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.id = "test_response_id"
            mock_response.output_text = "Test analysis result"
            mock_create.return_value = mock_response
            
            result = await client.analyze_metrics(sample_payload)
            
            assert result["status"] == "success"
            assert result["response_id"] == "test_response_id"
            assert result["analysis"] == "Test analysis result"
            assert len(result["metadata"]["releases_compared"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_recommendations_success(self):
        """Test getting recommendations"""
        client = LLMClient(folder_id="test", api_key="test")
        
        analysis_result = {
            "status": "success",
            "response_id": "test_id",
            "analysis": "Previous analysis"
        }
        
        with patch.object(client.client.responses, 'create', new_callable=AsyncMock) as mock_create:
            mock_response = MagicMock()
            mock_response.id = "rec_id"
            mock_response.output_text = "Recommendations"
            mock_create.return_value = mock_response
            
            result = await client.get_recommendations(analysis_result, priority="high")
            
            assert result["status"] == "success"
            assert result["analysis"] == "Recommendations"
    
    @pytest.mark.asyncio
    async def test_get_recommendations_failed_analysis(self):
        """Test recommendations fail with failed analysis"""
        client = LLMClient(folder_id="test", api_key="test")
        
        analysis_result = {
            "status": "error",
            "error": "Analysis failed"
        }
        
        result = await client.get_recommendations(analysis_result)
        
        assert result["status"] == "error"
        assert "Cannot generate recommendations" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])