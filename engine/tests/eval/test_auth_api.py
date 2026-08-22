"""登录与登出接口：转发数据服务、校验会话令牌。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import bdlh_runtime.run_api as run_api
from bdlh_runtime.data_client import DataServiceError


class FakeAuthData:
    def __init__(self) -> None:
        self.logins: list[dict[str, Any]] = []
        self.logged_out: list[str] = []

    def login(self, **kwargs: Any) -> dict[str, Any]:
        self.logins.append(kwargs)
        if kwargs["username"] == "owner" and kwargs["password"] == "secret":
            return {
                "accountId": "owner-id",
                "username": "owner",
                "token": "token-value",
                "expiresAt": "2026-08-21T00:00:00Z",
            }
        raise DataServiceError("用户名或密码错误", status_code=401)

    def logout(self, token: str) -> None:
        self.logged_out.append(token)


@pytest.fixture()
def fake_auth(monkeypatch: pytest.MonkeyPatch) -> FakeAuthData:
    data = FakeAuthData()
    monkeypatch.setattr(run_api, "_data", lambda: data)
    return data


@pytest.fixture()
def client(fake_auth: FakeAuthData) -> TestClient:
    return TestClient(run_api.app)


def test_login_returns_session(client: TestClient) -> None:
    response = client.post("/api/v1/login", json={"username": "owner", "password": "secret"})
    assert response.status_code == 200
    assert response.json()["token"] == "token-value"
    assert response.json()["expires_at"] == "2026-08-21T00:00:00Z"
    assert response.json()["username"] == "owner"


def test_login_forwards_client_metadata(client: TestClient, fake_auth: FakeAuthData) -> None:
    client.post(
        "/api/v1/login",
        json={"username": "owner", "password": "secret"},
        headers={"user-agent": "pytest"},
    )
    assert fake_auth.logins[0]["user_agent"] == "pytest"
    assert fake_auth.logins[0]["ip_address"] == "testclient"


def test_login_rejects_bad_credentials(client: TestClient) -> None:
    response = client.post("/api/v1/login", json={"username": "owner", "password": "wrong"})
    assert response.status_code == 401


def test_logout_revokes_session(client: TestClient, fake_auth: FakeAuthData) -> None:
    response = client.post("/api/v1/logout", headers={"Authorization": "Bearer token-value"})
    assert response.status_code == 200
    assert fake_auth.logged_out == ["token-value"]


def test_logout_without_token_is_rejected(client: TestClient) -> None:
    assert client.post("/api/v1/logout").status_code == 401
