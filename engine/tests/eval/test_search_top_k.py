"""GT-8 检索档 top_k 批次参数:设置后固定检索条数(单一变量),缺省=模型自报。"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import bdlh_runtime.run_api as run_api
from bdlh_runtime.engine.loader import ToolLoader
from bdlh_runtime.engine.loop import AgentLoop, AgentTurn
from bdlh_runtime.tools.catalog import catalog_from_snapshot
from bdlh_runtime.tools.search import SEARCH_TOOLS_NAME
from tests.engine.test_loop import FakeChatModel, _echo
from tests.eval.test_run_api import FakeDataClient, _auth
from tests.eval.test_visible_tools_config import _capture_conditions
from tests.helpers_encoder import LexicalEncoder
from tests.helpers_registry import seeded_snapshot

HIT_QUERY = "实时报价 最新价"


class CapturingLoader(ToolLoader):
    """记录 run_search 实际收到的 top_k(其余行为不变)。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.top_k_calls: list[int] = []

    def run_search(self, query: str, *, top_k: int, scene_tag: str, authenticated: bool) -> dict[str, object]:
        self.top_k_calls.append(top_k)
        return super().run_search(query, top_k=top_k, scene_tag=scene_tag, authenticated=authenticated)


def _search_call() -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            # 模型自报 top_k=8(合法上限)
            {"name": SEARCH_TOOLS_NAME, "args": {"query": HIT_QUERY, "top_k": 8}, "id": "s1", "type": "tool_call"}
        ],
    )


async def _run(loop: AgentLoop) -> Any:
    return await loop.run(AgentTurn(user_id="u1", message="宁德时代现在什么价", scene_tag="market"))


def _loader() -> CapturingLoader:
    return CapturingLoader(catalog_from_snapshot(seeded_snapshot()), tool_loading="search", encoder=LexicalEncoder())


@pytest.mark.asyncio
async def test_batch_top_k_overrides_model_reported_value() -> None:
    """设置 search_top_k=2:检索条数固定为 2,模型自报 8 被覆盖(单一变量纪律)。"""
    llm = FakeChatModel([_search_call(), AIMessage(content="已找到工具。")])
    loader = _loader()
    loop = AgentLoop(llm=llm, catalog=catalog_from_snapshot(seeded_snapshot()), executor=_echo,
                     loader=loader, search_top_k=2)
    result = await _run(loop)
    assert result.entered_loop is True
    assert loader.top_k_calls == [2]


@pytest.mark.asyncio
async def test_default_keeps_model_reported_top_k() -> None:
    """缺省(None):沿用现状——模型自报 8(_top_k 钳制 1..8)。"""
    llm = FakeChatModel([_search_call(), AIMessage(content="已找到工具。")])
    loader = _loader()
    loop = AgentLoop(llm=llm, catalog=catalog_from_snapshot(seeded_snapshot()), executor=_echo, loader=loader)
    await _run(loop)
    assert loader.top_k_calls == [8]


def test_search_top_k_persisted_and_validated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    data = FakeDataClient()
    monkeypatch.setattr(run_api, "_data", lambda: data)
    monkeypatch.setattr(run_api, "ARTIFACTS_DIR", tmp_path)
    client = TestClient(run_api.app)

    captured = _capture_conditions(
        client,
        data,
        monkeypatch,
        tmp_path,
        {"case_ids": ["research-01"], "runs": 1, "include_react": False, "search_top_k": 3},
    )
    assert captured["searchTopK"] == 3

    # 越界值拒绝(1..8 之外)
    for bad in (0, 9):
        response = client.post(
            "/api/v1/eval-batches",
            json={"case_ids": ["research-01"], "runs": 1, "include_react": False, "search_top_k": bad},
            headers=_auth(),
        )
        assert response.status_code == 422
