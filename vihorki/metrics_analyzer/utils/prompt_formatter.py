"""
Prompt formatting utilities for LLM analysis
"""

from typing import Optional
from ..models import MetricsPayload
from ..constants.prompts import ANALYSIS_PROMPT_TEMPLATE, format_focus_areas


def format_analysis_prompt(
    payload: MetricsPayload,
    focus_areas: Optional[list[str]] = None
) -> str:
    """
    Format analysis prompt from metrics payload using template.
    Automatically parses JSON and fills template with metrics.
    
    Args:
        payload: MetricsPayload with two releases
        focus_areas: Optional list of specific areas to focus on
        
    Returns:
        Formatted prompt string ready for LLM
    """
    if len(payload.releases) != 2:
        raise ValueError("Payload must contain exactly 2 releases")
    
    release_old = payload.releases[0]
    release_new = payload.releases[1]
    
    # Calculate percentages and changes
    old_total = release_old.release_info.total_visits
    new_total = release_new.release_info.total_visits
    
    old_new_users_pct = (release_old.aggregate_metrics.visits.new_users / old_total * 100) if old_total > 0 else 0
    old_returning_pct = (release_old.aggregate_metrics.visits.returning_users / old_total * 100) if old_total > 0 else 0
    new_new_users_pct = (release_new.aggregate_metrics.visits.new_users / new_total * 100) if new_total > 0 else 0
    new_returning_pct = (release_new.aggregate_metrics.visits.returning_users / new_total * 100) if new_total > 0 else 0
    
    # Calculate changes
    visits_change = new_total - old_total
    visits_change_pct = (visits_change / old_total * 100) if old_total > 0 else 0
    
    duration_change = (release_new.aggregate_metrics.visits.avg_duration_sec - 
                      release_old.aggregate_metrics.visits.avg_duration_sec)
    duration_change_pct = (duration_change / release_old.aggregate_metrics.visits.avg_duration_sec * 100) if release_old.aggregate_metrics.visits.avg_duration_sec > 0 else 0
    
    pages_change = (release_new.aggregate_metrics.visits.avg_page_views - 
                   release_old.aggregate_metrics.visits.avg_page_views)
    pages_change_pct = (pages_change / release_old.aggregate_metrics.visits.avg_page_views * 100) if release_old.aggregate_metrics.visits.avg_page_views > 0 else 0
    
    reverse_nav_change = (release_new.navigation_patterns.reverse_navigation.percentage - 
                         release_old.navigation_patterns.reverse_navigation.percentage)
    
    loops_change = (len(release_new.navigation_patterns.loop_patterns) - 
                   len(release_old.navigation_patterns.loop_patterns))
    
    high_interaction_change = (release_new.session_complexity_metrics.high_interaction_sessions.percentage - 
                               release_old.session_complexity_metrics.high_interaction_sessions.percentage)
    
    revisits_change = (release_new.session_complexity_metrics.url_revisit_patterns.percentage - 
                      release_old.session_complexity_metrics.url_revisit_patterns.percentage)
    
    # Format focus areas section
    focus_areas_section = format_focus_areas(focus_areas) if focus_areas else ""
    
    # Fill template
    return ANALYSIS_PROMPT_TEMPLATE.format(
        # Project info
        project_name=payload.metadata.project_name,
        
        # Release 1 (old)
        release_old_version=release_old.release_info.version,
        release_old_start=release_old.release_info.data_period.start.strftime("%Y-%m-%d %H:%M"),
        release_old_end=release_old.release_info.data_period.end.strftime("%Y-%m-%d %H:%M"),
        release_old_total_visits=old_total,
        release_old_unique_clients=release_old.release_info.unique_clients,
        release_old_total_hits=release_old.release_info.total_hits,
        release_old_new_users=release_old.aggregate_metrics.visits.new_users,
        release_old_new_users_pct=old_new_users_pct,
        release_old_returning_users=release_old.aggregate_metrics.visits.returning_users,
        release_old_returning_users_pct=old_returning_pct,
        release_old_avg_duration=release_old.aggregate_metrics.visits.avg_duration_sec,
        release_old_median_duration=release_old.aggregate_metrics.visits.median_duration_sec,
        release_old_avg_pages=release_old.aggregate_metrics.visits.avg_page_views,
        release_old_median_pages=release_old.aggregate_metrics.visits.median_page_views,
        release_old_reverse_nav=release_old.navigation_patterns.reverse_navigation.visits_with_reverse_nav,
        release_old_reverse_nav_pct=release_old.navigation_patterns.reverse_navigation.percentage,
        release_old_reverse_transitions=release_old.navigation_patterns.reverse_navigation.total_reverse_transitions,
        release_old_loops=len(release_old.navigation_patterns.loop_patterns),
        release_old_high_interaction=release_old.session_complexity_metrics.high_interaction_sessions.sessions_with_10plus_pages,
        release_old_high_interaction_pct=release_old.session_complexity_metrics.high_interaction_sessions.percentage,
        release_old_high_avg_pages=release_old.session_complexity_metrics.high_interaction_sessions.avg_pages,
        release_old_high_avg_duration=release_old.session_complexity_metrics.high_interaction_sessions.avg_duration_sec,
        release_old_revisits=release_old.session_complexity_metrics.url_revisit_patterns.sessions_with_url_revisits,
        release_old_revisits_pct=release_old.session_complexity_metrics.url_revisit_patterns.percentage,
        release_old_avg_revisits=release_old.session_complexity_metrics.url_revisit_patterns.avg_revisits_per_session,
        
        # Release 2 (new)
        release_new_version=release_new.release_info.version,
        release_new_start=release_new.release_info.data_period.start.strftime("%Y-%m-%d %H:%M"),
        release_new_end=release_new.release_info.data_period.end.strftime("%Y-%m-%d %H:%M"),
        release_new_total_visits=new_total,
        release_new_unique_clients=release_new.release_info.unique_clients,
        release_new_total_hits=release_new.release_info.total_hits,
        release_new_new_users=release_new.aggregate_metrics.visits.new_users,
        release_new_new_users_pct=new_new_users_pct,
        release_new_returning_users=release_new.aggregate_metrics.visits.returning_users,
        release_new_returning_pct=new_returning_pct,
        release_new_avg_duration=release_new.aggregate_metrics.visits.avg_duration_sec,
        release_new_median_duration=release_new.aggregate_metrics.visits.median_duration_sec,
        release_new_avg_pages=release_new.aggregate_metrics.visits.avg_page_views,
        release_new_median_pages=release_new.aggregate_metrics.visits.median_page_views,
        release_new_reverse_nav=release_new.navigation_patterns.reverse_navigation.visits_with_reverse_nav,
        release_new_reverse_nav_pct=release_new.navigation_patterns.reverse_navigation.percentage,
        release_new_reverse_transitions=release_new.navigation_patterns.reverse_navigation.total_reverse_transitions,
        release_new_loops=len(release_new.navigation_patterns.loop_patterns),
        release_new_high_interaction=release_new.session_complexity_metrics.high_interaction_sessions.sessions_with_10plus_pages,
        release_new_high_interaction_pct=release_new.session_complexity_metrics.high_interaction_sessions.percentage,
        release_new_high_avg_pages=release_new.session_complexity_metrics.high_interaction_sessions.avg_pages,
        release_new_high_avg_duration=release_new.session_complexity_metrics.high_interaction_sessions.avg_duration_sec,
        release_new_revisits=release_new.session_complexity_metrics.url_revisit_patterns.sessions_with_url_revisits,
        release_new_revisits_pct=release_new.session_complexity_metrics.url_revisit_patterns.percentage,
        release_new_avg_revisits=release_new.session_complexity_metrics.url_revisit_patterns.avg_revisits_per_session,
        
        # Changes
        visits_change=visits_change,
        visits_change_pct=visits_change_pct,
        duration_change=duration_change,
        duration_change_pct=duration_change_pct,
        pages_change=pages_change,
        pages_change_pct=pages_change_pct,
        reverse_nav_change=reverse_nav_change,
        loops_change=loops_change,
        high_interaction_change=high_interaction_change,
        revisits_change=revisits_change,
        
        # Focus areas
        focus_areas_section=focus_areas_section
    )