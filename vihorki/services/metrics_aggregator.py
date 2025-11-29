"""
Metrics Aggregation Service.
Aggregates raw visit/hit data into MetricsPayload format for LLM analysis.
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from statistics import median

from sqlalchemy import select, func, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from vihorki.infrastructure.postgres.on_startup.init_tables import VisitTable, HitTable
from vihorki.metrics_analyzer.models import (
    MetricsPayload, Metadata, Release, ReleaseInfo, DataPeriod,
    AggregateMetrics, VisitsMetrics, PageViewsMetrics,
    SessionDistribution, DistributionBucket,
    DeviceBreakdown, DeviceCategoryMetric, SegmentMetric,
    TrafficSources, GeographicDistribution, PageMetric,
    NavigationPatterns, ReverseNavigation, PageTransition, LoopPattern,
    FunnelMetrics, FunnelStep,
    SessionComplexityMetrics, HighInteractionSessions, URLRevisitPatterns
)

logger = logging.getLogger(__name__)


class MetricsAggregator:
    """
    Service to aggregate visits and hits data into MetricsPayload format.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def aggregate_for_periods(
        self,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
        version1: str = "v1.0.0",
        version2: str = "v2.0.0",
        project_name: str = "Analytics Project",
        target_urls: Optional[List[str]] = None
    ) -> MetricsPayload:
        """
        Aggregate metrics for two time periods and create MetricsPayload.
        
        Args:
            period1_start, period1_end: First period (baseline release)
            period2_start, period2_end: Second period (comparison release)
            version1, version2: Version labels for releases
            project_name: Project name for metadata
            target_urls: Optional list of URLs to focus analysis on
            
        Returns:
            MetricsPayload ready for LLM analysis
        """
        logger.info(f"Aggregating metrics for periods: {period1_start}-{period1_end} vs {period2_start}-{period2_end}")
        
        # Get release data for both periods
        release1 = await self._aggregate_release(
            period1_start, period1_end, version1, target_urls
        )
        release2 = await self._aggregate_release(
            period2_start, period2_end, version2, target_urls
        )
        
        return MetricsPayload(
            metadata=Metadata(
                project_name=project_name,
                generated_at=datetime.utcnow(),
                data_source="postgres_analytics"
            ),
            releases=[release1, release2]
        )

    async def _aggregate_release(
        self,
        start: datetime,
        end: datetime,
        version: str,
        target_urls: Optional[List[str]] = None
    ) -> Release:
        """Aggregate all metrics for a single release period."""
        
        # Fetch visits in period
        visits = await self._fetch_visits(start, end)
        
        if not visits:
            logger.warning(f"No visits found for period {start} - {end}")
            return self._create_empty_release(start, end, version)
        
        # Fetch hits for these visits
        all_watch_ids = []
        for v in visits:
            if v.watch_ids:
                all_watch_ids.extend([wid.strip() for wid in v.watch_ids.split(',') if wid.strip()])
        
        hits = await self._fetch_hits(all_watch_ids) if all_watch_ids else []
        
        # Build URL to hits mapping
        url_to_hits = defaultdict(list)
        for hit in hits:
            if hit.url:
                url_to_hits[hit.url].append(hit)
        
        # Calculate all metrics
        release_info = self._calc_release_info(visits, hits, start, end, version)
        aggregate_metrics = self._calc_aggregate_metrics(visits, hits)
        session_distribution = self._calc_session_distribution(visits)
        device_breakdown = self._calc_device_breakdown(visits)
        traffic_sources = self._calc_traffic_sources(visits)
        geographic_distribution = self._calc_geographic_distribution(visits)
        page_metrics = self._calc_page_metrics(visits, hits, url_to_hits, target_urls)
        navigation_patterns = await self._calc_navigation_patterns(visits, hits)
        funnel_metrics = self._calc_funnel_metrics(visits, target_urls)
        session_complexity = self._calc_session_complexity(visits, hits)
        
        return Release(
            release_info=release_info,
            aggregate_metrics=aggregate_metrics,
            session_distribution=session_distribution,
            device_breakdown=device_breakdown,
            traffic_sources=traffic_sources,
            geographic_distribution=geographic_distribution,
            page_metrics=page_metrics,
            navigation_patterns=navigation_patterns,
            funnel_metrics=funnel_metrics,
            session_complexity_metrics=session_complexity
        )

    async def _fetch_visits(self, start: datetime, end: datetime) -> List[VisitTable]:
        """Fetch visits within time period."""
        # Make datetimes naive for comparison
        if start.tzinfo:
            start = start.replace(tzinfo=None)
        if end.tzinfo:
            end = end.replace(tzinfo=None)
            
        stmt = select(VisitTable).where(
            VisitTable.date_time.between(start, end)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _fetch_hits(self, watch_ids: List[str]) -> List[HitTable]:
        """Fetch hits by watch IDs."""
        if not watch_ids:
            return []
        stmt = select(HitTable).where(HitTable.watch_id.in_(watch_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _calc_release_info(
        self, 
        visits: List[VisitTable], 
        hits: List[HitTable],
        start: datetime, 
        end: datetime, 
        version: str
    ) -> ReleaseInfo:
        """Calculate release info metrics."""
        unique_clients = len(set(v.client_id for v in visits if v.client_id))
        
        return ReleaseInfo(
            version=version,
            data_period=DataPeriod(start=start, end=end),
            total_visits=len(visits),
            total_hits=len(hits),
            unique_clients=unique_clients
        )

    def _calc_aggregate_metrics(
        self, 
        visits: List[VisitTable], 
        hits: List[HitTable]
    ) -> AggregateMetrics:
        """Calculate aggregate visit and page view metrics."""
        total_visits = len(visits)
        new_users = sum(1 for v in visits if v.is_new_user)
        returning_users = total_visits - new_users
        
        page_views_list = [v.page_views or 0 for v in visits]
        durations = [v.visit_duration or 0 for v in visits]
        
        avg_page_views = sum(page_views_list) / total_visits if total_visits else 0
        median_page_views = int(median(page_views_list)) if page_views_list else 0
        avg_duration = int(sum(durations) / total_visits) if total_visits else 0
        median_duration = int(median(durations)) if durations else 0
        total_duration = sum(durations)
        
        unique_urls = len(set(h.url for h in hits if h.url))
        
        return AggregateMetrics(
            visits=VisitsMetrics(
                total_count=total_visits,
                new_users=new_users,
                returning_users=returning_users,
                avg_page_views=round(avg_page_views, 2),
                median_page_views=median_page_views,
                avg_duration_sec=avg_duration,
                median_duration_sec=median_duration,
                total_duration_sec=total_duration
            ),
            page_views=PageViewsMetrics(
                total_count=len(hits),
                unique_urls=unique_urls
            )
        )

    def _calc_session_distribution(self, visits: List[VisitTable]) -> SessionDistribution:
        """Calculate session distribution by page views and duration."""
        # Page views distribution buckets
        pv_buckets = [
            (1, 1), (2, 5), (6, 10), (11, None)
        ]
        # Duration buckets (seconds)
        dur_buckets = [
            (0, 30), (31, 120), (121, 300), (301, None)
        ]
        
        total = len(visits)
        
        def calc_distribution(visits: List[VisitTable], getter, buckets) -> List[DistributionBucket]:
            result = []
            for min_val, max_val in buckets:
                if max_val is None:
                    count = sum(1 for v in visits if (getter(v) or 0) >= min_val)
                else:
                    count = sum(1 for v in visits if min_val <= (getter(v) or 0) <= max_val)
                pct = round(count / total * 100, 1) if total else 0
                result.append(DistributionBucket(
                    range_min=min_val,
                    range_max=max_val,
                    count=count,
                    percentage=pct
                ))
            return result
        
        return SessionDistribution(
            by_page_views=calc_distribution(visits, lambda v: v.page_views, pv_buckets),
            by_duration_sec=calc_distribution(visits, lambda v: v.visit_duration, dur_buckets)
        )

    def _calc_device_breakdown(self, visits: List[VisitTable]) -> DeviceBreakdown:
        """Calculate device breakdown metrics."""
        total = len(visits)
        
        def calc_segment_metrics(visits_subset: List[VisitTable], segment_value: str) -> Dict[str, Any]:
            count = len(visits_subset)
            pct = round(count / total * 100, 1) if total else 0
            avg_pv = round(sum(v.page_views or 0 for v in visits_subset) / count, 1) if count else 0
            avg_dur = int(sum(v.visit_duration or 0 for v in visits_subset) / count) if count else 0
            single_page = sum(1 for v in visits_subset if (v.page_views or 0) == 1)
            return {
                'segment_value': segment_value,
                'visits': count,
                'percentage': pct,
                'avg_page_views': avg_pv,
                'avg_duration_sec': avg_dur,
                'single_page_visits': single_page
            }
        
        # By category
        by_category = []
        for cat in [1, 2]:
            subset = [v for v in visits if v.device_category == cat]
            if subset:
                metrics = calc_segment_metrics(subset, "Desktop" if cat == 1 else "Mobile/Tablet")
                by_category.append(DeviceCategoryMetric(device_category=cat, **metrics))
        
        # By OS
        os_counter = Counter(v.operating_system for v in visits if v.operating_system)
        by_os = []
        for os_name, count in os_counter.most_common(10):
            subset = [v for v in visits if v.operating_system == os_name]
            metrics = calc_segment_metrics(subset, os_name)
            by_os.append(SegmentMetric(**metrics))
        
        # By browser
        browser_counter = Counter(v.browser for v in visits if v.browser)
        by_browser = []
        for browser, count in browser_counter.most_common(10):
            subset = [v for v in visits if v.browser == browser]
            metrics = calc_segment_metrics(subset, browser)
            by_browser.append(SegmentMetric(**metrics))
        
        # By screen orientation
        orient_counter = Counter(v.screen_orientation_name for v in visits if v.screen_orientation_name)
        by_orientation = []
        for orient, count in orient_counter.most_common():
            subset = [v for v in visits if v.screen_orientation_name == orient]
            metrics = calc_segment_metrics(subset, orient)
            by_orientation.append(SegmentMetric(**metrics))
        
        return DeviceBreakdown(
            by_category=by_category if by_category else [
                DeviceCategoryMetric(device_category=1, segment_value="Desktop", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)
            ],
            by_os=by_os if by_os else [SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)],
            by_browser=by_browser if by_browser else [SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)],
            by_screen_orientation=by_orientation if by_orientation else [SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)]
        )

    def _calc_traffic_sources(self, visits: List[VisitTable]) -> TrafficSources:
        """Calculate traffic source metrics."""
        total = len(visits)
        
        engine_counter = Counter(v.last_search_engine_root for v in visits if v.last_search_engine_root)
        by_search_engine = []
        
        for engine, count in engine_counter.most_common(10):
            subset = [v for v in visits if v.last_search_engine_root == engine]
            pct = round(count / total * 100, 1) if total else 0
            avg_pv = round(sum(v.page_views or 0 for v in subset) / count, 1) if count else 0
            avg_dur = int(sum(v.visit_duration or 0 for v in subset) / count) if count else 0
            single_page = sum(1 for v in subset if (v.page_views or 0) == 1)
            
            by_search_engine.append(SegmentMetric(
                segment_value=engine,
                visits=count,
                percentage=pct,
                avg_page_views=avg_pv,
                avg_duration_sec=avg_dur,
                single_page_visits=single_page
            ))
        
        if not by_search_engine:
            by_search_engine = [SegmentMetric(
                segment_value="direct",
                visits=total,
                percentage=100.0,
                avg_page_views=0,
                avg_duration_sec=0,
                single_page_visits=0
            )]
        
        return TrafficSources(by_search_engine=by_search_engine)

    def _calc_geographic_distribution(self, visits: List[VisitTable]) -> GeographicDistribution:
        """Calculate geographic distribution metrics."""
        total = len(visits)
        
        city_counter = Counter(v.region_city for v in visits if v.region_city)
        top_cities = []
        
        for city, count in city_counter.most_common(15):
            subset = [v for v in visits if v.region_city == city]
            pct = round(count / total * 100, 1) if total else 0
            avg_pv = round(sum(v.page_views or 0 for v in subset) / count, 1) if count else 0
            avg_dur = int(sum(v.visit_duration or 0 for v in subset) / count) if count else 0
            single_page = sum(1 for v in subset if (v.page_views or 0) == 1)
            
            top_cities.append(SegmentMetric(
                segment_value=city,
                visits=count,
                percentage=pct,
                avg_page_views=avg_pv,
                avg_duration_sec=avg_dur,
                single_page_visits=single_page
            ))
        
        if not top_cities:
            top_cities = [SegmentMetric(
                segment_value="Unknown",
                visits=total,
                percentage=100.0,
                avg_page_views=0,
                avg_duration_sec=0,
                single_page_visits=0
            )]
        
        return GeographicDistribution(top_cities=top_cities)

    def _calc_page_metrics(
        self,
        visits: List[VisitTable],
        hits: List[HitTable],
        url_to_hits: Dict[str, List[HitTable]],
        target_urls: Optional[List[str]] = None
    ) -> List[PageMetric]:
        """Calculate per-page metrics."""
        result = []
        
        # Get top URLs by hit count
        url_counter = Counter(h.url for h in hits if h.url)
        
        if target_urls:
            urls_to_analyze = target_urls
        else:
            urls_to_analyze = [url for url, _ in url_counter.most_common(20)]
        
        for url in urls_to_analyze:
            url_hits = url_to_hits.get(url, [])
            
            # Visits where this URL is entry/exit
            visits_as_entry = sum(1 for v in visits if v.start_url == url)
            visits_as_exit = sum(1 for v in visits if v.end_url == url)
            
            # Total hits and unique visitors
            total_hits = len(url_hits)
            unique_clients = len(set(h.client_id for h in url_hits if h.client_id))
            
            # Single page visits starting at this URL
            single_page = sum(1 for v in visits if v.start_url == url and (v.page_views or 0) == 1)
            
            # Get title from hits
            titles = [h.title for h in url_hits if h.title]
            title = titles[0] if titles else url.split('/')[-1] or "Page"
            
            # Subsequent page diversity (simplified - count unique next URLs)
            # This would require more complex analysis of hit sequences
            subsequent_diversity = min(10, len(set(h.url for h in hits if h.url and h.url != url)))
            
            result.append(PageMetric(
                url=url,
                title=title[:100],  # Truncate title
                visits_as_entry=visits_as_entry,
                visits_as_exit=visits_as_exit,
                total_hits=total_hits,
                unique_visitors=unique_clients,
                visits_with_single_page=single_page,
                subsequent_page_diversity=subsequent_diversity
            ))
        
        if not result:
            result = [PageMetric(
                url="/",
                title="Home",
                visits_as_entry=len(visits),
                visits_as_exit=len(visits),
                total_hits=len(hits),
                unique_visitors=len(set(v.client_id for v in visits)),
                visits_with_single_page=sum(1 for v in visits if (v.page_views or 0) == 1),
                subsequent_page_diversity=0
            )]
        
        return result

    async def _calc_navigation_patterns(
        self,
        visits: List[VisitTable],
        hits: List[HitTable]
    ) -> NavigationPatterns:
        """Calculate navigation pattern metrics."""
        total_visits = len(visits)
        
        # Build visit to hits mapping
        visit_hits: Dict[str, List[HitTable]] = defaultdict(list)
        hit_by_watch_id = {h.watch_id: h for h in hits}
        
        for visit in visits:
            if not visit.watch_ids:
                continue
            watch_ids = [wid.strip() for wid in visit.watch_ids.split(',') if wid.strip()]
            for wid in watch_ids:
                if wid in hit_by_watch_id:
                    visit_hits[str(visit.visit_id)].append(hit_by_watch_id[wid])
        
        # Analyze reverse navigation
        visits_with_reverse = 0
        total_reverse_transitions = 0
        transitions_counter: Counter = Counter()
        loop_counter: Counter = Counter()
        
        for visit_id, v_hits in visit_hits.items():
            # Sort hits by datetime
            sorted_hits = sorted(v_hits, key=lambda h: h.datetime_hit or datetime.min)
            urls = [h.url for h in sorted_hits if h.url]
            
            if len(urls) < 2:
                continue
            
            # Check for reverse navigation
            seen_urls = set()
            has_reverse = False
            reverse_count = 0
            
            for i, url in enumerate(urls):
                if url in seen_urls:
                    has_reverse = True
                    reverse_count += 1
                seen_urls.add(url)
            
            if has_reverse:
                visits_with_reverse += 1
                total_reverse_transitions += reverse_count
            
            # Count transitions
            for i in range(len(urls) - 1):
                transitions_counter[(urls[i], urls[i + 1])] += 1
            
            # Detect loops (simplified: A->B->A pattern)
            for i in range(len(urls) - 2):
                if urls[i] == urls[i + 2] and urls[i] != urls[i + 1]:
                    loop_counter[tuple(urls[i:i + 3])] += 1
        
        reverse_pct = round(visits_with_reverse / total_visits * 100, 1) if total_visits else 0
        
        # Top transitions
        common_transitions = [
            PageTransition(from_url=from_url, to_url=to_url, transition_count=count)
            for (from_url, to_url), count in transitions_counter.most_common(10)
        ]
        
        if not common_transitions:
            common_transitions = [PageTransition(from_url="/", to_url="/page", transition_count=0)]
        
        # Top loop patterns
        loop_patterns = [
            LoopPattern(sequence=list(seq), occurrences=count)
            for seq, count in loop_counter.most_common(5)
        ]
        
        if not loop_patterns:
            loop_patterns = [LoopPattern(sequence=["/"], occurrences=0)]
        
        return NavigationPatterns(
            reverse_navigation=ReverseNavigation(
                visits_with_reverse_nav=visits_with_reverse,
                percentage=reverse_pct,
                total_reverse_transitions=total_reverse_transitions
            ),
            common_transitions=common_transitions,
            loop_patterns=loop_patterns
        )

    def _calc_funnel_metrics(
        self,
        visits: List[VisitTable],
        target_urls: Optional[List[str]] = None
    ) -> FunnelMetrics:
        """Calculate funnel metrics."""
        # Use target URLs or common entry/exit points
        if target_urls and len(target_urls) >= 2:
            funnel_urls = target_urls[:5]
        else:
            # Use most common start URLs
            start_counter = Counter(v.start_url for v in visits if v.start_url)
            funnel_urls = [url for url, _ in start_counter.most_common(3)]
        
        if not funnel_urls:
            return FunnelMetrics(application_funnel=[
                FunnelStep(step=1, url="/", visits_entered=len(visits), visits_completed=len(visits))
            ])
        
        steps = []
        for i, url in enumerate(funnel_urls, 1):
            entered = sum(1 for v in visits if v.start_url == url or url in (v.end_url or ''))
            completed = sum(1 for v in visits if v.end_url == url) if i < len(funnel_urls) else entered
            
            steps.append(FunnelStep(
                step=i,
                url=url,
                visits_entered=entered,
                visits_completed=completed
            ))
        
        return FunnelMetrics(application_funnel=steps)

    def _calc_session_complexity(
        self,
        visits: List[VisitTable],
        hits: List[HitTable]
    ) -> SessionComplexityMetrics:
        """Calculate session complexity metrics."""
        total_visits = len(visits)
        
        # High interaction sessions (10+ pages)
        high_interaction = [v for v in visits if (v.page_views or 0) >= 10]
        hi_count = len(high_interaction)
        hi_pct = round(hi_count / total_visits * 100, 1) if total_visits else 0
        hi_avg_pages = round(sum(v.page_views or 0 for v in high_interaction) / hi_count, 1) if hi_count else 0
        hi_avg_duration = int(sum(v.visit_duration or 0 for v in high_interaction) / hi_count) if hi_count else 0
        
        # Estimate unique URLs per session (simplified)
        hi_avg_unique_urls = min(hi_avg_pages * 0.8, 20) if hi_count else 0
        
        # URL revisit patterns
        # Build visit to URL counts
        hit_by_watch_id = {h.watch_id: h for h in hits}
        sessions_with_revisits = 0
        total_revisits = 0
        total_unique_revisited = 0
        
        for visit in visits:
            if not visit.watch_ids:
                continue
            watch_ids = [wid.strip() for wid in visit.watch_ids.split(',') if wid.strip()]
            urls = [hit_by_watch_id[wid].url for wid in watch_ids if wid in hit_by_watch_id and hit_by_watch_id[wid].url]
            
            url_counts = Counter(urls)
            revisited = {url: count - 1 for url, count in url_counts.items() if count > 1}
            
            if revisited:
                sessions_with_revisits += 1
                total_revisits += sum(revisited.values())
                total_unique_revisited += len(revisited)
        
        revisit_pct = round(sessions_with_revisits / total_visits * 100, 1) if total_visits else 0
        avg_revisits = round(total_revisits / sessions_with_revisits, 1) if sessions_with_revisits else 0
        avg_unique_revisited = round(total_unique_revisited / sessions_with_revisits, 1) if sessions_with_revisits else 0
        
        return SessionComplexityMetrics(
            high_interaction_sessions=HighInteractionSessions(
                sessions_with_10plus_pages=hi_count,
                percentage=hi_pct,
                avg_pages=hi_avg_pages,
                avg_duration_sec=hi_avg_duration,
                avg_unique_urls=round(hi_avg_unique_urls, 1)
            ),
            url_revisit_patterns=URLRevisitPatterns(
                sessions_with_url_revisits=sessions_with_revisits,
                percentage=revisit_pct,
                avg_revisits_per_session=avg_revisits,
                avg_unique_urls_revisited=avg_unique_revisited
            )
        )

    def _create_empty_release(self, start: datetime, end: datetime, version: str) -> Release:
        """Create an empty release with zero metrics."""
        return Release(
            release_info=ReleaseInfo(
                version=version,
                data_period=DataPeriod(start=start, end=end),
                total_visits=0,
                total_hits=0,
                unique_clients=0
            ),
            aggregate_metrics=AggregateMetrics(
                visits=VisitsMetrics(
                    total_count=0, new_users=0, returning_users=0,
                    avg_page_views=0, median_page_views=0,
                    avg_duration_sec=0, median_duration_sec=0, total_duration_sec=0
                ),
                page_views=PageViewsMetrics(total_count=0, unique_urls=0)
            ),
            session_distribution=SessionDistribution(
                by_page_views=[DistributionBucket(range_min=1, range_max=1, count=0, percentage=0)],
                by_duration_sec=[DistributionBucket(range_min=0, range_max=30, count=0, percentage=0)]
            ),
            device_breakdown=DeviceBreakdown(
                by_category=[DeviceCategoryMetric(device_category=1, segment_value="Desktop", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)],
                by_os=[SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)],
                by_browser=[SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)],
                by_screen_orientation=[SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)]
            ),
            traffic_sources=TrafficSources(
                by_search_engine=[SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)]
            ),
            geographic_distribution=GeographicDistribution(
                top_cities=[SegmentMetric(segment_value="Unknown", visits=0, percentage=0, avg_page_views=0, avg_duration_sec=0, single_page_visits=0)]
            ),
            page_metrics=[PageMetric(url="/", title="Home", visits_as_entry=0, visits_as_exit=0, total_hits=0, unique_visitors=0, visits_with_single_page=0, subsequent_page_diversity=0)],
            navigation_patterns=NavigationPatterns(
                reverse_navigation=ReverseNavigation(visits_with_reverse_nav=0, percentage=0, total_reverse_transitions=0),
                common_transitions=[PageTransition(from_url="/", to_url="/", transition_count=0)],
                loop_patterns=[LoopPattern(sequence=["/"], occurrences=0)]
            ),
            funnel_metrics=FunnelMetrics(application_funnel=[FunnelStep(step=1, url="/", visits_entered=0, visits_completed=0)]),
            session_complexity_metrics=SessionComplexityMetrics(
                high_interaction_sessions=HighInteractionSessions(sessions_with_10plus_pages=0, percentage=0, avg_pages=0, avg_duration_sec=0, avg_unique_urls=0),
                url_revisit_patterns=URLRevisitPatterns(sessions_with_url_revisits=0, percentage=0, avg_revisits_per_session=0, avg_unique_urls_revisited=0)
            )
        )

