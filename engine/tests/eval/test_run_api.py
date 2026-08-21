"""私有运行 API：固定题号、fail-closed 鉴权和数据服务持久化。"""

from __future__ import annotations

import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

import bdlh_runtime.run_api as run_api


class FakeDataClient:
    def __init__(self) -> None:
        self.created_runs: list[dict[str, Any]] = []
        self.completed: list[str] = []

    def list_cases(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "research-01",
                "version": 1,
                "title": "实时行情工具选择",
                "message": "宁德时代现在什么价",
                "scene": "market",
                "authenticated": False,
                "expectedChecks": {
                    "category": "金融研究",
                    "expected_tools": ["market.get_realtime_quote"],
                },
                "steps": [],
            }
        ]

    def create_batch(self, **_: Any) -> str:
        return "batch-1"

    def get_batch(self, batch_id: str) -> dict[str, Any]:
        return {"id": batch_id, "status": "COMPLETE", "runs": []}

    def verify_session(self, token: str) -> dict[str, Any] | None:
        if token == "test-token":
            return {"accountId": "owner", "username": "owner"}
        return None

    def create_run(self, payload: dict[str, Any]) -> str:
        self.created_runs.append(payload)
        return f"run-{len(self.created_runs)}"

    def complete_batch(self, batch_id: str, status: str) -> None:
        assert batch_id == "batch-1"
        assert status in {"COMPLETE", "FAILED"}

    def save_evaluation(self, run_id: str, **_: Any) -> None:
        assert run_id.startswith("run-")

    def complete_run(self, run_id: str, output: dict[str, Any]) -> None:
        assert "aggregate" in output
        self.completed.append(run_id)


@pytest.fixture()
def fake_data(monkeypatch: pytest.MonkeyPatch) -> FakeDataClient:
    data = FakeDataClient()
    monkeypatch.setattr(run_api, "_data", lambda: data)
    return data


@pytest.fixture()
def client(fake_data: FakeDataClient) -> TestClient:
    return TestClient(run_api.app)


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "touchstone-run-api"


def test_requires_session_token(client: TestClient) -> None:
    assert client.get("/api/v1/cases").status_code == 401


def test_cases_are_read_from_data_service(client: TestClient) -> None:
    response = client.get("/api/v1/cases", headers=_auth())
    assert response.status_code == 200
    assert response.json()[0]["id"] == "research-01"


def test_completed_batch_can_be_read_after_job_memory_is_gone(client: TestClient) -> None:
    response = client.get("/api/v1/batches/batch-1", headers=_auth())
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETE"


def test_request_rejects_question_or_tool_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/eval-batches",
        json={"case_ids": ["research-01"], "message": "任意问题"},
        headers=_auth(),
    )
    assert response.status_code == 422


def test_batch_persists_each_agent_mode(
    client: TestClient,
    fake_data: FakeDataClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        run_api,
        "_execute_eval",
        lambda _request, _catalog: {
            "cases": [
                {
                    "id": "research-01",
                    "baseline": {"tool_correct": 1},
                    "react": {"tool_correct": 1},
                    "treatment": {"tool_correct": 1},
                    "lineage": [],
                }
            ]
        },
    )
    response = client.post(
        "/api/v1/eval-batches",
        json={"case_ids": ["research-01"], "runs": 1},
        headers=_auth(),
    )
    assert response.status_code == 200
    job_id = response.json()["job_id"]

    job = _poll(client, job_id)
    assert job["status"] == "done"
    assert [item["agentMode"] for item in fake_data.created_runs] == [
        "baseline-tool-calling",
        "langgraph-react",
        "full-system",
    ]
    assert len(fake_data.completed) == 3


def test_unknown_case_is_rejected(client: TestClient) -> None:
    response = client.post("/api/v1/eval-batches", json={"case_ids": ["missing"]}, headers=_auth())
    assert response.status_code == 400


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def _poll(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(50):
        response = client.get(f"/api/v1/jobs/{job_id}", headers=_auth())
        assert response.status_code == 200
        if response.json()["status"] != "running":
            return response.json()
        time.sleep(0.02)
    raise AssertionError("作业未完成")
