"""
Analysis Orchestrator - coordinates API client and LLM agent
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .models import MetricsPayload
from .clients.api import APIClient
from .clients.llm import LLMClient

logger = logging.getLogger(__name__)


class AnalysisOrchestrator:
    """
    Orchestrates the complete analysis workflow:
    1. Receives metrics data
    2. Sends to metrics API endpoint
    3. Analyzes with LLM agent
    4. Returns comprehensive results
    """

    def __init__(
        self,
        metrics_api_url: str,
        metrics_api_key: Optional[str] = None,
        yandex_folder_id: Optional[str] = None,
        yandex_api_key: Optional[str] = None,
        llm_model: str = "qwen3-235b-a22b-fp8"
    ):
        """
        Initialize the orchestrator with both clients.

        Args:
            metrics_api_url: URL for metrics API endpoint
            metrics_api_key: Optional API key for metrics endpoint
            yandex_folder_id: Yandex Cloud folder ID
            yandex_api_key: Yandex Cloud API key
            llm_model: LLM model to use for analysis
        """
        self.api_client = APIClient(
            base_url=metrics_api_url,
            api_key=metrics_api_key
        )
        
        self.llm_client = LLMClient(
            folder_id=yandex_folder_id,
            api_key=yandex_api_key,
            model=llm_model
        )

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self):
        """Close all clients"""
        await self.api_client.close()

    async def analyze_and_submit(
        self,
        payload: MetricsPayload,
        submit_to_api: bool = True,
        analyze_with_llm: bool = True,
        focus_areas: Optional[List[str]] = None,
        reasoning_effort: str = "medium"
    ) -> Dict[str, Any]:
        """
        Complete analysis workflow: validate, submit, and analyze metrics.

        Args:
            payload: MetricsPayload with metrics data
            submit_to_api: Whether to submit to metrics API
            analyze_with_llm: Whether to analyze with LLM
            focus_areas: Optional specific areas to focus on in analysis
            reasoning_effort: LLM reasoning effort level

        Returns:
            Complete analysis results
        """
        logger.info("Validating metrics payload")
        is_valid, error_msg = self.api_client.validate_payload(payload)
        
        if not is_valid:
            logger.error(f"Validation failed: {error_msg}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "project": payload.metadata.project_name,
                "validation": {
                    "status": "failed",
                    "error": error_msg
                }
            }
            
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "project": payload.metadata.project_name,
            "releases": [
                payload.releases[0].release_info.version,
                payload.releases[1].release_info.version
            ]
        }

        results["validation"] = {"status": "passed"}
        logger.info("Validation passed")

        if submit_to_api:
            logger.info("Submitting metrics to API")
            try:
                api_response = await self.api_client.send_metrics(payload)
                results["api_submission"] = api_response
                
                if api_response["status"] != "success":
                    logger.warning(f"API submission failed: {api_response.get('error')}")
                else:
                    logger.info("Metrics submitted successfully")
                    
            except Exception as e:
                logger.error(f"API submission error: {str(e)}")
                results["api_submission"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            results["api_submission"] = {"status": "skipped"}

        if analyze_with_llm:
            logger.info("Starting LLM analysis")
            try:
                llm_response = await self.llm_client.analyze_metrics(
                    payload=payload,
                    focus_areas=focus_areas,
                    reasoning_effort=reasoning_effort
                )
                results["llm_analysis"] = llm_response
                
                if llm_response["status"] == "success":
                    logger.info("LLM analysis completed successfully")
                else:
                    logger.warning(f"LLM analysis failed: {llm_response.get('error')}")
                    
            except Exception as e:
                logger.error(f"LLM analysis error: {str(e)}")
                results["llm_analysis"] = {
                    "status": "error",
                    "error": str(e)
                }
        else:
            results["llm_analysis"] = {"status": "skipped"}

        return results

    async def get_detailed_recommendations(
        self,
        analysis_result: Dict[str, Any],
        priority: str = "high"
    ) -> Dict[str, Any]:
        """
        Get detailed recommendations based on previous analysis.

        Args:
            analysis_result: Previous analysis result from analyze_and_submit
            priority: Priority level for recommendations

        Returns:
            Detailed recommendations
        """
        if "llm_analysis" not in analysis_result:
            return {
                "status": "error",
                "error": "No LLM analysis found in results"
            }

        llm_analysis = analysis_result["llm_analysis"]
        
        if llm_analysis.get("status") != "success":
            return {
                "status": "error",
                "error": "Cannot generate recommendations from failed analysis"
            }

        return await self.llm_client.get_recommendations(
            llm_analysis,
            priority=priority
        )

    async def compare_releases(
        self,
        payload: MetricsPayload
    ) -> Dict[str, Any]:
        """
        Perform detailed comparison between two releases.

        Args:
            payload: MetricsPayload with two releases

        Returns:
            Comparison results
        """
        if len(payload.releases) != 2:
            return {
                "status": "error",
                "error": "Exactly 2 releases required for comparison"
            }

        release_old = payload.releases[0]
        release_new = payload.releases[1]

        comparison = {
            "status": "success",
            "releases": {
                "old": release_old.release_info.version,
                "new": release_new.release_info.version
            },
            "metrics_comparison": {}
        }

        metrics_comp = comparison["metrics_comparison"]

        metrics_comp["visits"] = {
            "total_change": release_new.release_info.total_visits - release_old.release_info.total_visits,
            "total_change_pct": (
                (release_new.release_info.total_visits - release_old.release_info.total_visits) 
                / release_old.release_info.total_visits * 100
            ) if release_old.release_info.total_visits > 0 else 0,
            "avg_duration_change": (
                release_new.aggregate_metrics.visits.avg_duration_sec 
                - release_old.aggregate_metrics.visits.avg_duration_sec
            ),
            "avg_page_views_change": (
                release_new.aggregate_metrics.visits.avg_page_views 
                - release_old.aggregate_metrics.visits.avg_page_views
            )
        }

        metrics_comp["navigation"] = {
            "reverse_nav_change_pct": (
                release_new.navigation_patterns.reverse_navigation.percentage 
                - release_old.navigation_patterns.reverse_navigation.percentage
            ),
            "loop_patterns_change": (
                len(release_new.navigation_patterns.loop_patterns) 
                - len(release_old.navigation_patterns.loop_patterns)
            )
        }

        metrics_comp["complexity"] = {
            "high_interaction_change_pct": (
                release_new.session_complexity_metrics.high_interaction_sessions.percentage 
                - release_old.session_complexity_metrics.high_interaction_sessions.percentage
            ),
            "url_revisits_change_pct": (
                release_new.session_complexity_metrics.url_revisit_patterns.percentage 
                - release_old.session_complexity_metrics.url_revisit_patterns.percentage
            )
        }

        concerns = []
        
        if metrics_comp["navigation"]["reverse_nav_change_pct"] > 5:
            concerns.append("Significant increase in reverse navigation")
        
        if metrics_comp["navigation"]["loop_patterns_change"] > 0:
            concerns.append("More loop patterns detected")
        
        if metrics_comp["complexity"]["url_revisits_change_pct"] > 5:
            concerns.append("Increase in URL revisit patterns")
        
        if metrics_comp["visits"]["avg_duration_change"] > 30:
            concerns.append("Sessions taking longer (possible confusion)")

        comparison["concerns"] = concerns
        comparison["concern_level"] = "high" if len(concerns) >= 3 else "medium" if len(concerns) >= 1 else "low"

        return comparison

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all components.

        Returns:
            Health status of all services
        """
        health = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }

        try:
            metrics_healthy = await self.api_client.health_check()
            health["services"]["metrics_api"] = {
                "status": "healthy" if metrics_healthy else "unhealthy"
            }
        except Exception as e:
            health["services"]["metrics_api"] = {
                "status": "error",
                "error": str(e)
            }

        try:
            health["services"]["llm_client"] = {
                "status": "configured",
                "model": self.llm_client.model
            }
        except Exception as e:
            health["services"]["llm_client"] = {
                "status": "error",
                "error": str(e)
            }

        all_healthy = all(
            svc.get("status") in ["healthy", "configured"] 
            for svc in health["services"].values()
        )
        health["overall_status"] = "healthy" if all_healthy else "degraded"

        return health
