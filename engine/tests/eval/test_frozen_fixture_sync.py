"""冻结工具返回种子同步守卫。

数据库 init.sql 的冻结数据段是 ``fixture_tool_responses`` 的唯一真源；单测注入的
``tests/eval/frozen_fixtures.py`` payload 是替身。两者漂移（改了一处忘另一处）即失败。

GT-2 起 ab-eval 集的增量行经 ``db/postgresql/changes/`` 脚本交付（不回改 init.sql），
守卫按 init.sql → changes/*.sql（文件名序）拼接提取，镜像需与两者合并结果一致。
"""

from __future__ import annotations

import re
from pathlib import Path

from tests.eval.frozen_fixtures import FROZEN_RESPONSES

_REPO = Path(__file__).resolve().parents[3]
_SEED_SQL = _REPO / "db" / "postgresql" / "setup" / "init.sql"
_CHANGES_DIR = _REPO / "db" / "postgresql" / "changes"

# 只匹配 ab-eval 集行：负例集（ab-eval-negative-v1 等）集名不同，不会误匹配。
_ROW_PATTERN = re.compile(r"^\('ab-eval', 1, '([^']+)', '([^']+)'", re.MULTILINE)


def _ab_eval_section(text: str) -> str:
    start = text.index("INSERT INTO touchstone.fixture_tool_responses")
    return text[start : text.index(";", start)]


def _source_texts() -> list[str]:
    """ab-eval 冻结行的 SQL 来源：init.sql 段 + changes/*.sql 中的同表 INSERT 段。"""
    texts = [_ab_eval_section(_SEED_SQL.read_text(encoding="utf-8"))]
    for script in sorted(_CHANGES_DIR.glob("*.sql")):
        content = script.read_text(encoding="utf-8")
        if "INSERT INTO touchstone.fixture_tool_responses" in content:
            texts.append(_ab_eval_section(content))
    return texts


def _seed_rows() -> list[tuple[str, str]]:
    """按 sequence 顺序提取 (call_key, tool_name) 行。"""
    rows: list[tuple[str, str]] = []
    for text in _source_texts():
        rows.extend(_ROW_PATTERN.findall(text))
    return rows


def test_frozen_fixture_rows_match_seed_in_order():
    assert _seed_rows() == [(key, tool) for key, tool, _ in FROZEN_RESPONSES], (
        "冻结工具返回清单与数据库 seed(init.sql + changes/) 不一致（含顺序，即 sequence 语义）"
    )


def test_seed_rows_are_all_success_for_frozen_lookup():
    """FrozenObservations 只收 SUCCESS 行；ab-eval 集全部为 SUCCESS 才能整表生效。"""
    statuses: list[str] = []
    for text in _source_texts():
        statuses.extend(re.findall(r"'(SUCCESS|FAILED|ERROR|TIMEOUT)'", text))
    assert statuses and set(statuses) == {"SUCCESS"}, (
        "ab-eval 集出现非 SUCCESS 行，需同步调整替身与查找语义（负例请落 ab-eval-negative-v1）"
    )
