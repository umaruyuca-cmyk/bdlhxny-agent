"""FrozenObservations 查找语义：覆盖键优先、基准回退、未知工具失败桩。"""

from __future__ import annotations

import pytest

from bdlh_runtime.evaluation.frozen_observations import FrozenObservations
from tests.eval.frozen_fixtures import frozen_payload


@pytest.fixture()
def frozen() -> FrozenObservations:
    return FrozenObservations(frozen_payload())


def test_symbol_override_takes_precedence(frozen: FrozenObservations) -> None:
    assert frozen.get("market.get_realtime_quote", {"symbol": "600519"})["price"] == 1685.00


def test_base_key_fallback_when_no_override(frozen: FrozenObservations) -> None:
    assert frozen.get("market.get_realtime_quote", {"symbol": "300750"})["price"] == 185.50


def test_arguments_optional(frozen: FrozenObservations) -> None:
    assert frozen.get("market.get_realtime_quote")["symbol"] == "300750"


def test_unknown_tool_returns_failure_stub(frozen: FrozenObservations) -> None:
    assert frozen.get("market.no_such_tool", {"symbol": "300750"}) == {
        "status": "FAILED",
        "error": "unknown tool: market.no_such_tool",
    }


def test_payload_without_success_rows_is_rejected() -> None:
    with pytest.raises(ValueError, match="no SUCCESS responses"):
        FrozenObservations({"responses": [{"call_key": "x", "response_status": "FAILED", "response": {}}]})
