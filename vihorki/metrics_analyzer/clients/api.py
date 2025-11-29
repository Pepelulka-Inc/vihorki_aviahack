"""
API Client for sending metrics to external endpoint
"""

import httpx
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from ..models import MetricsPayload

logger = logging.getLogger(__name__)


class APIClient:
    """
    Client for sending metrics to the analysis API endpoint.
    Implements the OpenAPI contract for /metrics POST endpoint.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the metrics API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def close(self):
        """Close the HTTP client"""
        await self._client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional authentication"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def send_metrics(
        self,
        payload: MetricsPayload,
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Send metrics payload to the API endpoint.

        Args:
            payload: MetricsPayload object containing all metrics data
            validate: Whether to validate the payload before sending

        Returns:
            Response from the API

        Raises:
            httpx.HTTPStatusError: If the API returns an error status
            ValueError: If payload validation fails
        """
        if validate:
            if len(payload.releases) != 2:
                raise ValueError(
                    f"Payload must contain exactly 2 releases, got {len(payload.releases)}"
                )

        endpoint = f"{self.base_url}/metrics"
        
        try:
            logger.info(f"Sending metrics to {endpoint}")
            logger.debug(f"Payload: {payload.model_dump_json(indent=2)}")

            response = await self._client.post(
                endpoint,
                json=payload.model_dump(mode='json'),
                headers=self._get_headers()
            )

            response.raise_for_status()
            
            logger.info(f"Metrics sent successfully. Status: {response.status_code}")
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "response": response.json() if response.content else {}
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error",
                "status_code": e.response.status_code,
                "error": e.response.text
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    async def send_metrics_dict(
        self,
        metrics_dict: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send metrics from a dictionary (useful for testing or external data).

        Args:
            metrics_dict: Dictionary containing metrics data

        Returns:
            Response from the API
        """
        payload = MetricsPayload(**metrics_dict)
        return await self.send_metrics(payload)

    def validate_payload(self, payload: MetricsPayload) -> tuple[bool, Optional[str]]:
        """
        Validate metrics payload structure.

        Args:
            payload: MetricsPayload to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if len(payload.releases) != 2:
                return False, f"Must have exactly 2 releases, got {len(payload.releases)}"

            if not payload.metadata.project_name:
                return False, "Project name is required"

            for idx, release in enumerate(payload.releases):
                if release.release_info.total_visits < 0:
                    return False, f"Release {idx}: total_visits cannot be negative"
                
                if release.release_info.total_hits < 0:
                    return False, f"Release {idx}: total_hits cannot be negative"

                if release.release_info.data_period.start >= release.release_info.data_period.end:
                    return False, f"Release {idx}: start date must be before end date"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def health_check(self) -> bool:
        """
        Check if the API endpoint is reachable.

        Returns:
            True if endpoint is healthy, False otherwise
        """
        try:
            response = await self._client.get(
                f"{self.base_url}/health",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False