"""冻结工具返回种子同步守卫。

数据库 seed（08 SQL）是 ``fixture_tool_responses`` 的唯一真源；单测注入的
``tests/eval/frozen_fixtures.py`` payload 是替身。两者漂移（改了一处忘另一处）即失败。
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.eval.frozen_fixtures import FROZEN_RESPONSES

_SEED_SQL = Path(__file__).resolve().parents[3] / "db" / "postgresql" / "setup" / "08-seed-tool-fixtures.sql"


def _seed_rows() -> list[tuple[str, str]]:
    """按 sequence 顺序提取 (call_key, tool_name) 行。"""
    text = _SEED_SQL.read_text(encoding="utf-8")
    start = text.index("INSERT INTO touchstone.fixture_tool_responses")
    section = text[start : text.index(";", start)]
    return re.findall(r"^\('ab-eval', 1, '([^']+)', '([^']+)'", section, re.MULTILINE)


def test_frozen_fixture_rows_match_seed_in_order():
    assert _seed_rows() == [(key, tool) for key, tool, _ in FROZEN_RESPONSES], (
        "冻结工具返回清单与数据库 seed 08 不一致（含顺序，即 sequence 语义）"
    )


def test_seed_rows_are_all_success_for_frozen_lookup():
    """FrozenObservations 只收 SUCCESS 行；seed 全部为 SUCCESS 才能整表生效。"""
    text = _SEED_SQL.read_text(encoding="utf-8")
    start = text.index("INSERT INTO touchstone.fixture_tool_responses")
    section = text[start : text.index(";", start)]
    statuses = re.findall(r"'(SUCCESS|FAILED|ERROR|TIMEOUT)'", section)
    assert statuses and set(statuses) == {"SUCCESS"}, "seed 08 出现非 SUCCESS 行，需同步调整替身与查找语义"
