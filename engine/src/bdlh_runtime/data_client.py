"""data 服务的内部 HTTP 客户端。

运行服务不直接连接 PostgreSQL；固定题库和运行记录统一经过数据服务读写。
"""

from __future__ import annotations

import os
from typing import Any

import httpx


class DataServiceError(RuntimeError):
    """数据服务不可用或拒绝请求。"""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DataClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self._base_url = (base_url or os.getenv("DATA_API_BASE_URL", "http://data:8080/internal/v1")).rstrip("/")
        self._token = token if token is not None else os.getenv("DATA_INTERNAL_TOKEN", "")

    def list_cases(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/cases")
        if not isinstance(payload, list):
            raise DataServiceError("data service returned an invalid case catalog")
        return payload

    def get_tool_catalog(self) -> dict[str, Any]:
        payload = self._request("GET", "/tool-catalog")
        if not isinstance(payload, dict):
            raise DataServiceError("data service returned an invalid tool catalog")
        return payload

    def get_tool_fixtures(self, fixture_set_id: str, *, version: int = 1) -> dict[str, Any]:
        payload = self._request("GET", f"/tool-fixtures/{fixture_set_id}?version={version}")
        if not isinstance(payload, dict):
            raise DataServiceError("data service returned an invalid tool fixture set")
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

    def login(
        self,
        *,
        username: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        status, response = self._request_raw(
            "POST",
            "/auth/login",
            json={"username": username, "password": password, "ipAddress": ip_address, "userAgent": user_agent},
        )
        if status == 200:
            return response.json()
        raise DataServiceError(_error_message(response, "登录失败"), status_code=status)

    def verify_session(self, token: str) -> dict[str, Any] | None:
        status, response = self._request_raw("POST", "/auth/verify", json={"token": token})
        if status == 200:
            return response.json()
        return None

    def logout(self, token: str) -> None:
        self._request_raw("POST", "/auth/logout", json={"token": token})

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        expect_json: bool = True,
    ) -> Any:
        status, response = self._request_raw(method, path, json=json)
        response.raise_for_status()
        return response.json() if expect_json else None

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> tuple[int, httpx.Response]:
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
            return response.status_code, response
        except httpx.HTTPError as exc:
            raise DataServiceError(f"data service request failed: {method} {path}: {exc}") from exc


def _error_message(response: httpx.Response, default: str) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and body.get("error"):
            return str(body["error"])
    except (ValueError, AttributeError):
        pass
    return default
