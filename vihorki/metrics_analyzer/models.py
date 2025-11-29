"""
Data models for UX Metrics Analysis based on OpenAPI contract
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Metadata(BaseModel):
    """Metadata about the metrics payload"""
    project_name: str
    generated_at: datetime
    data_source: str


class DataPeriod(BaseModel):
    """Time period for data collection"""
    start: datetime
    end: datetime


class ReleaseInfo(BaseModel):
    """Information about a specific release"""
    version: str
    data_period: DataPeriod
    total_visits: int = Field(ge=0)
    total_hits: int = Field(ge=0)
    unique_clients: int = Field(ge=0)


class VisitsMetrics(BaseModel):
    """Aggregate metrics for visits"""
    total_count: int
    new_users: int
    returning_users: int
    avg_page_views: float
    median_page_views: int
    avg_duration_sec: int
    median_duration_sec: int
    total_duration_sec: int


class PageViewsMetrics(BaseModel):
    """Aggregate metrics for page views"""
    total_count: int
    unique_urls: int


class AggregateMetrics(BaseModel):
    """Aggregated metrics from visits and hits tables"""
    visits: VisitsMetrics
    page_views: PageViewsMetrics


class DistributionBucket(BaseModel):
    """Distribution bucket for session metrics"""
    range_min: int
    range_max: Optional[int] = None
    count: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)


class SessionDistribution(BaseModel):
    """Distribution of sessions by various metrics"""
    by_page_views: List[DistributionBucket]
    by_duration_sec: List[DistributionBucket]


class SegmentMetric(BaseModel):
    """Base model for segment-based metrics"""
    segment_value: str
    visits: int
    percentage: float
    avg_page_views: float
    avg_duration_sec: int
    single_page_visits: int


class DeviceCategoryMetric(SegmentMetric):
    """Device category specific metric"""
    device_category: int = Field(ge=1, le=2)  # 1=desktop, 2=mobile/tablet


class DeviceBreakdown(BaseModel):
    """Breakdown of metrics by device characteristics"""
    by_category: List[DeviceCategoryMetric]
    by_os: List[SegmentMetric]
    by_browser: List[SegmentMetric]
    by_screen_orientation: List[SegmentMetric]


class TrafficSources(BaseModel):
    """Traffic source analysis"""
    by_search_engine: List[SegmentMetric]


class GeographicDistribution(BaseModel):
    """Geographic distribution of users"""
    top_cities: List[SegmentMetric]


class PageMetric(BaseModel):
    """Metrics for individual pages"""
    url: str
    title: str
    visits_as_entry: int
    visits_as_exit: int
    total_hits: int
    unique_visitors: int
    visits_with_single_page: int
    subsequent_page_diversity: int


class PageTransition(BaseModel):
    """Page-to-page transition data"""
    from_url: str
    to_url: str
    transition_count: int


class LoopPattern(BaseModel):
    """Detected loop patterns in navigation"""
    sequence: List[str]
    occurrences: int


class ReverseNavigation(BaseModel):
    """Reverse navigation analysis"""
    visits_with_reverse_nav: int
    percentage: float
    total_reverse_transitions: int


class NavigationPatterns(BaseModel):
    """Navigation pattern analysis"""
    reverse_navigation: ReverseNavigation
    common_transitions: List[PageTransition]
    loop_patterns: List[LoopPattern]


class FunnelStep(BaseModel):
    """Single step in a conversion funnel"""
    step: int
    url: str
    visits_entered: int
    visits_completed: int


class FunnelMetrics(BaseModel):
    """Funnel analysis metrics"""
    application_funnel: List[FunnelStep]


class HighInteractionSessions(BaseModel):
    """Metrics for high-interaction sessions"""
    sessions_with_10plus_pages: int
    percentage: float
    avg_pages: float
    avg_duration_sec: int
    avg_unique_urls: float


class URLRevisitPatterns(BaseModel):
    """URL revisit pattern analysis"""
    sessions_with_url_revisits: int
    percentage: float
    avg_revisits_per_session: float
    avg_unique_urls_revisited: float


class SessionComplexityMetrics(BaseModel):
    """Complex session behavior metrics"""
    high_interaction_sessions: HighInteractionSessions
    url_revisit_patterns: URLRevisitPatterns


class Release(BaseModel):
    """Complete release data with all metrics"""
    release_info: ReleaseInfo
    aggregate_metrics: AggregateMetrics
    session_distribution: SessionDistribution
    device_breakdown: DeviceBreakdown
    traffic_sources: TrafficSources
    geographic_distribution: GeographicDistribution
    page_metrics: List[PageMetric]
    navigation_patterns: NavigationPatterns
    funnel_metrics: FunnelMetrics
    session_complexity_metrics: SessionComplexityMetrics


class MetricsPayload(BaseModel):
    """Complete metrics payload for API submission"""
    metadata: Metadata
    releases: List[Release] = Field(min_length=2, max_length=2)

    class Config:
        json_schema_extra = {
            "example": {
                "metadata": {
                    "project_name": "Example Project",
                    "generated_at": "2025-01-01T00:00:00Z",
                    "data_source": "analytics_db"
                },
                "releases": [
                    # Two releases for comparison
                ]
            }
        }