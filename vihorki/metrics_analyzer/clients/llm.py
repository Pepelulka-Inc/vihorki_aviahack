"""
LLM Client for communicating with Yandex Cloud AI
"""

import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import logging

from ..models import MetricsPayload
from ..constants.prompts import SYSTEM_INSTRUCTION, RECOMMENDATIONS_PROMPT_TEMPLATE, METRIC_EXPLANATION_PROMPT
from ..utils.prompt_formatter import format_analysis_prompt

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for communicating with Yandex Cloud AI agents.
    Uses OpenAI-compatible Responses API for analysis.
    """

    def __init__(
        self,
        folder_id: Optional[str] = None,
        api_key: Optional[str] = None,
        model: str = "qwen3-235b-a22b-fp8",
        base_url: str = "https://rest-assistant.api.cloud.yandex.net/v1"
    ):
        """
        Initialize LLM client for Yandex Cloud.

        Args:
            folder_id: Yandex Cloud folder ID
            api_key: Yandex Cloud API key
            model: Model name to use
            base_url: Base URL for Yandex Cloud API
        """
        self.folder_id = folder_id or os.getenv('YANDEX_FOLDER_ID')
        self.api_key = api_key or os.getenv('YANDEX_API_KEY')
        
        if not self.folder_id or not self.api_key:
            raise ValueError(
                "folder_id and api_key must be provided or set in environment variables "
                "(YANDEX_FOLDER_ID, YANDEX_API_KEY)"
            )

        self.model = f"gpt://{self.folder_id}/{model}/latest"
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=self.api_key,
            project=self.folder_id
        )

    async def analyze_metrics(
        self,
        payload: MetricsPayload,
        focus_areas: Optional[List[str]] = None,
        reasoning_effort: str = "medium"
    ) -> Dict[str, Any]:
        """
        Analyze metrics using LLM agent.

        Args:
            payload: MetricsPayload with two releases to compare
            focus_areas: Optional list of specific areas to focus on
            reasoning_effort: Reasoning effort level (low, medium, high)

        Returns:
            Analysis results from LLM
        """
        if len(payload.releases) != 2:
            raise ValueError("Payload must contain exactly 2 releases for comparison")

        user_input = format_analysis_prompt(payload, focus_areas)

        try:
            logger.info("Sending metrics to LLM for analysis")
            
            response = await self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTION,
                input=user_input,
                reasoning={"effort": reasoning_effort},
                store=True
            )

            logger.info("Analysis completed successfully")

            return {
                "status": "success",
                "response_id": response.id,
                "analysis": response.output_text,
                "metadata": {
                    "model": self.model,
                    "reasoning_effort": reasoning_effort,
                    "releases_compared": [
                        payload.releases[0].release_info.version,
                        payload.releases[1].release_info.version
                    ]
                }
            }

        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def continue_analysis(
        self,
        previous_response_id: str,
        follow_up_question: str
    ) -> Dict[str, Any]:
        """
        Continue previous analysis with follow-up question.

        Args:
            previous_response_id: ID of previous response
            follow_up_question: Follow-up question or request

        Returns:
            Continued analysis results
        """
        try:
            response = await self.client.responses.create(
                model=self.model,
                previous_response_id=previous_response_id,
                input=follow_up_question,
                store=True
            )

            return {
                "status": "success",
                "response_id": response.id,
                "analysis": response.output_text
            }

        except Exception as e:
            logger.error(f"Follow-up analysis failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def get_recommendations(
        self,
        analysis_result: Dict[str, Any],
        priority: str = "high"
    ) -> Dict[str, Any]:
        """
        Get specific recommendations based on analysis.

        Args:
            analysis_result: Previous analysis result
            priority: Priority level for recommendations (high, medium, low)

        Returns:
            Recommendations from LLM
        """
        if analysis_result.get("status") != "success":
            return {
                "status": "error",
                "error": "Cannot generate recommendations from failed analysis"
            }

        follow_up = RECOMMENDATIONS_PROMPT_TEMPLATE.format(priority=priority)

        return await self.continue_analysis(
            analysis_result["response_id"],
            follow_up
        )

    async def explain_metric(
        self,
        metric_name: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get explanation of a specific metric.

        Args:
            metric_name: Name of the metric to explain
            context: Optional context about the metric

        Returns:
            Explanation from LLM
        """
        context_text = f"\n\nКонтекст: {context}" if context else ""
        prompt = METRIC_EXPLANATION_PROMPT.format(
            metric_name=metric_name,
            context=context_text
        )

        try:
            response = await self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTION,
                input=prompt
            )

            return {
                "status": "success",
                "explanation": response.output_text
            }

        except Exception as e:
            logger.error(f"Metric explanation failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }