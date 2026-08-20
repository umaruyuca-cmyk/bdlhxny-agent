"""data 服务的内部 HTTP 客户端。

运行服务不直接连接 PostgreSQL；固定题库和运行记录统一经过数据服务读写。
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class DataServiceError(RuntimeError):
    """数据服务不可用或拒绝请求。"""


class DataClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self._base_url = (base_url or os.getenv("DATA_API_BASE_URL", "http://data:8080/internal/v1")).rstrip(
            "/"
        )
        self._token = token if token is not None else os.getenv("DATA_INTERNAL_TOKEN", "")

    def list_cases(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/cases")
        if not isinstance(payload, list):
            raise DataServiceError("data service returned an invalid case catalog")
        return payload

    def create_batch(self, *, name: str, fixed_conditions: dict[str, Any]) -> str:
        payload = self._request(
            "POST",
            "/batches",
            json={"name": name, "experimentType": "agent-implementation", "fixedConditions": fixed_conditions},
        )
        return str(payload["batchId"])

    def create_run(self, payload: dict[str, Any]) -> str:
        result = self._request("POST", "/runs", json=payload)
        return str(result["runId"])

    def get_batch(self, batch_id: str) -> dict[str, Any]:
        payload = self._request("GET", f"/batches/{batch_id}")
        if not isinstance(payload, dict):
            raise DataServiceError("data service returned an invalid batch")
        return payload

    def complete_batch(self, batch_id: str, status: str) -> None:
        self._request(
            "POST",
            f"/batches/{batch_id}/complete",
            json={"status": status},
            expect_json=False,
        )

    def save_evaluation(self, run_id: str, *, checks: dict[str, Any], metrics: dict[str, Any]) -> None:
        self._request(
            "POST",
            f"/runs/{run_id}/evaluation",
            json={
                "evaluatorVersion": "fixed-rules-v1",
                "validRun": True,
                "status": "COMPLETE",
                "checks": checks,
                "metrics": metrics,
            },
            expect_json=False,
        )

    def complete_run(self, run_id: str, output: dict[str, Any]) -> None:
        self._request(
            "POST",
            f"/runs/{run_id}/complete",
            json={"status": "COMPLETE", "output": output},
            expect_json=False,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> Any:
        if not self._token.strip():
            raise DataServiceError("DATA_INTERNAL_TOKEN is not configured")
        try:
            response = httpx.request(
                method,
                f"{self._base_url}{path}",
                headers={"X-Internal-Token": self._token},
                json=json,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json() if expect_json else None
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise DataServiceError(f"data service request failed: {method} {path}: {exc}") from exc
