"""模型切换:按账号的 LLM 接入配置(查/存/连通性测试)与批次接线。

安全契约:
- 对外 API 永不回明文密钥(仅 hasApiKey/keyLast4);
- 发起批次时读取发起者配置构建客户端,密钥不得进入
  fixed_conditions / model_config / 运行请求 / 任何工件载荷。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import bdlh_runtime.run_api as run_api

SECRET = "sk-live-abcdef123456"


class FakeLlmData:
    def __init__(self) -> None:
        self.configs: dict[str, dict[str, Any]] = {}
        self.batch_fixed_conditions: list[dict[str, Any]] = []

    # -- 登录会话 --
    def verify_session(self, token: str) -> dict[str, Any] | None:
        return {"accountId": "acct-1", "username": "owner"} if token == "t" else None

    # -- 题库与批次(最小面) --
    def list_cases(self) -> list[dict[str, Any]]:
        return [{"id": "research-01", "variants": [{"variantId": "default"}]}]

    def get_tool_catalog(self) -> dict[str, Any]:
        return {"capabilities": []}

    def create_batch(self, *, name: str, fixed_conditions: dict[str, Any]) -> str:
        self.batch_fixed_conditions.append(fixed_conditions)
        return "batch-1"

    def complete_batch(self, batch_id: str, status: str) -> None:
        pass

    # -- LLM 配置 --
    def get_llm_config(self, account_id: str) -> dict[str, Any] | None:
        return self.configs.get(account_id)

    def save_llm_config(self, account_id: str, *, base_url: str, model: str, api_key: str | None) -> dict[str, Any]:
        current = self.configs.get(account_id) or {}
        merged_key = api_key if api_key is not None else current.get("apiKey")
        if api_key == "":
            merged_key = None
        self.configs[account_id] = {"baseUrl": base_url, "model": model, "apiKey": merged_key}
        return {"baseUrl": base_url, "model": model}


@pytest.fixture()
def fake_data(monkeypatch: pytest.MonkeyPatch) -> FakeLlmData:
    data = FakeLlmData()
    monkeypatch.setattr(run_api, "_data", lambda: data)
    return data


@pytest.fixture()
def client(fake_data: FakeLlmData) -> TestClient:
    return TestClient(run_api.app)


def _auth() -> dict[str, str]:
    return {"Authorization": "Bearer t"}


def test_get_config_unconfigured(client: TestClient) -> None:
    resp = client.get("/api/v1/llm-config", headers=_auth())
    assert resp.status_code == 200
    assert resp.json()["configured"] is False


def test_save_then_get_returns_sanitized_view(client: TestClient, fake_data: FakeLlmData) -> None:
    resp = client.put(
        "/api/v1/llm-config",
        json={"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat", "api_key": SECRET},
        headers=_auth(),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["configured"] is True
    assert body["model"] == "deepseek-chat"
    assert body["keyLast4"] == SECRET[-4:]
    assert SECRET not in resp.text, "对外 API 不得回明文密钥"

    view = client.get("/api/v1/llm-config", headers=_auth()).json()
    assert SECRET not in str(view)


def test_probe_endpoint_reports_provider_errors(
    client: TestClient, fake_data: FakeLlmData, monkeypatch: pytest.MonkeyPatch
) -> None:
    client.put(
        "/api/v1/llm-config",
        json={"base_url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4.7-flash", "api_key": SECRET},
        headers=_auth(),
    )
    monkeypatch.setattr(run_api, "_probe_llm", lambda b, m, k: (False, "HTTP 429: 余额不足"))
    resp = client.post("/api/v1/llm-config/test", headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "余额不足" in body["detail"]
    assert SECRET not in resp.text

    monkeypatch.setattr(run_api, "_probe_llm", lambda b, m, k: (True, "连接成功,模型可用"))
    assert client.post("/api/v1/llm-config/test", headers=_auth()).json()["ok"] is True


def test_batch_reads_requester_config_and_keeps_secret_out(
    client: TestClient, fake_data: FakeLlmData, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """发起批次读取发起者配置;密钥绝不进入 fixed_conditions。"""
    client.put(
        "/api/v1/llm-config",
        json={"base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat", "api_key": SECRET},
        headers=_auth(),
    )
    monkeypatch.setattr(run_api, "ARTIFACTS_DIR", tmp_path)
    captured: dict[str, Any] = {}

    def fake_execute(
        _request: Any, _catalog: Any, job: Any = None, llm_config: Any = None
    ) -> tuple[dict[str, Any], list[Any]]:
        captured["llm_config"] = llm_config
        return {"cases": [], "run_records": []}, []

    monkeypatch.setattr(run_api, "_execute_eval", fake_execute)
    resp = client.post(
        "/api/v1/eval-batches",
        json={"case_ids": ["research-01"], "runs": 1, "include_react": False},
        headers=_auth(),
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    for _ in range(50):
        job = client.get(f"/api/v1/jobs/{job_id}", headers=_auth()).json()
        if job["status"] != "running":
            break
        import time

        time.sleep(0.02)
    assert job["status"] == "done"
    assert captured["llm_config"] is not None
    assert captured["llm_config"]["apiKey"] == SECRET  # 内部构建客户端可用
    for fixed in fake_data.batch_fixed_conditions:
        assert SECRET not in str(fixed), "密钥不得进入 fixed_conditions"


def test_account_config_model_overrides_request_default(
    client: TestClient, fake_data: FakeLlmData, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """账号绑定的模型必须覆盖请求默认(env 缺省),否则会把错误模型名发给另一提供商。

    回归:配置切到硅基流动后,请求默认仍取服务端 env 的 glm 标签,
    发给硅基流动必然 400 Model does not exist,整批数据失效。
    """
    client.put(
        "/api/v1/llm-config",
        json={"base_url": "https://api.siliconflow.cn/v1", "model": "Qwen/Qwen3.6-35B-A3B", "api_key": SECRET},
        headers=_auth(),
    )
    monkeypatch.setattr(run_api, "ARTIFACTS_DIR", tmp_path)

    def fake_execute(
        _request: Any, _catalog: Any, job: Any = None, llm_config: Any = None
    ) -> tuple[dict[str, Any], list[Any]]:
        return {"run_records": []}, []

    monkeypatch.setattr(run_api, "_execute_eval", fake_execute)
    resp = client.post(
        "/api/v1/eval-batches",
        json={"case_ids": ["research-01"], "runs": 1, "include_react": False},
        headers=_auth(),
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    for _ in range(50):
        job = client.get(f"/api/v1/jobs/{job_id}", headers=_auth()).json()
        if job["status"] != "running":
            break
        import time

        time.sleep(0.02)
    assert job["status"] == "done"
    fixed = fake_data.batch_fixed_conditions[-1]
    assert fixed["model"] == "Qwen/Qwen3.6-35B-A3B", "批次记录的模型必须与账号配置一致"
    assert job["request"]["model"] == "Qwen/Qwen3.6-35B-A3B"
