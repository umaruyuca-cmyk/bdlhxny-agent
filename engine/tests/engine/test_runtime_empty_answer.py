"""runtime 空答案兜底：降级与正常路径空答案的文案/审计码分开，不掩盖异常。"""

from __future__ import annotations

from types import SimpleNamespace

from bdlh_runtime.engine.contracts import (
    EMPTY_ANSWER_AUDIT,
    EMPTY_ANSWER_REASON,
    RESPOND_UNAVAILABLE_REASON,
    InputEvent,
)
from bdlh_runtime.engine.runtime import _execution_from_result


def _event() -> InputEvent:
    return InputEvent(event_id="e1", user_id="user-1", session_id="s1", run_id="r1", message="问题")


def _result(answer: str = "", degraded: bool = False) -> SimpleNamespace:
    return SimpleNamespace(
        answer=answer,
        audits=[],
        fastpath_name=None,
        degraded=degraded,
        observations=[],
        entered_loop=True,
        loaded_tools=[],
    )


def test_degraded_empty_answer_keeps_unavailable_copy() -> None:
    execution = _execution_from_result(_event(), _result(degraded=True))
    assert execution.response.message == RESPOND_UNAVAILABLE_REASON
    assert EMPTY_ANSWER_AUDIT not in execution.response.audit_codes


def test_normal_empty_answer_is_flagged_not_masked() -> None:
    execution = _execution_from_result(_event(), _result())
    assert execution.response.message == EMPTY_ANSWER_REASON
    assert EMPTY_ANSWER_AUDIT in execution.response.audit_codes


def test_nonempty_answer_untouched() -> None:
    execution = _execution_from_result(_event(), _result(answer="正常回答"))
    assert execution.response.message == "正常回答"
    assert EMPTY_ANSWER_AUDIT not in execution.response.audit_codes
