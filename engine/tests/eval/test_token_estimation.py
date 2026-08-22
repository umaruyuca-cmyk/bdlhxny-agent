"""token 估算口径标注：API 不回 usage 时按 chars//4 近似并显式标记。"""

from __future__ import annotations

from types import SimpleNamespace

from bdlh_runtime.evaluation.ab_eval import _extract_treatment_tokens
from bdlh_runtime.evaluation.baseline_agent import _extract_tokens


class TestExtractTreatmentTokens:
    def test_usage_metadata_marks_not_estimated(self) -> None:
        msg = SimpleNamespace(
            content="hi",
            usage_metadata=SimpleNamespace(input_tokens=10, output_tokens=5),
        )
        prompt, completion, estimated = _extract_treatment_tokens(SimpleNamespace(messages=[msg]))
        assert (prompt, completion, estimated) == (10, 5, False)

    def test_missing_usage_marks_estimated(self) -> None:
        msg = SimpleNamespace(content="x" * 8)  # 无 usage_metadata / response_metadata
        prompt, completion, estimated = _extract_treatment_tokens(SimpleNamespace(messages=[msg]))
        assert (prompt, completion) == (0, 2)
        assert estimated is True


class TestExtractTokens:
    def test_openai_format_marks_not_estimated(self) -> None:
        msg = SimpleNamespace(
            content="hi",
            response_metadata={"token_usage": {"prompt_tokens": 7, "completion_tokens": 3}},
        )
        assert _extract_tokens(msg) == (7, 3, False)

    def test_fallback_marks_estimated(self) -> None:
        msg = SimpleNamespace(content="x" * 12)
        assert _extract_tokens(msg) == (0, 3, True)
