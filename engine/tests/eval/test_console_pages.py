"""docs 站评测页面与真源同步守卫。

- 固定题库页（cases.html）必须覆盖数据库 seed 全部题号与题目原文——题库改了页面没改即失败；
- 工具清单页（tools.html）必须覆盖工具目录全量工具名——目录增删工具页面未跟上即失败；
- 评测结果页（results.html）必须消费评测命令导出的 report.json。
"""

from __future__ import annotations

import re
from pathlib import Path

from bdlh_runtime.registry import load_and_validate
from bdlh_runtime.tools.catalog import catalog_from_snapshot
from tests.registry.seeded_store import build_seeded_store

_CONSOLE_DOCS = Path(__file__).resolve().parents[3] / "web" / "public" / "docs"
_INIT_SQL = Path(__file__).resolve().parents[3] / "db" / "postgresql" / "setup" / "init.sql"


def _seed_cases() -> list[tuple[str, str]]:
    """从数据库 init.sql 的固定用例段（唯一真源）提取 (case_id, message)。"""
    text = _INIT_SQL.read_text(encoding="utf-8")
    start = text.index("INSERT INTO touchstone.case_versions")
    section = text[start : text.index(";", start)]
    return re.findall(r"^\('([a-z]+-\d+)', 1, '([^']+)'", section, re.MULTILINE)


def test_cases_page_lists_all_eval_cases():
    cases = _seed_cases()
    assert len(cases) >= 18, "seed 应至少包含 18 道固定题"
    html = (_CONSOLE_DOCS / "cases.html").read_text(encoding="utf-8")
    for case_id, message in cases:
        assert case_id in html, f"固定题库页缺少题号 {case_id}"
        assert message in html, f"固定题库页缺少题目原文 {case_id}：{message}"


def test_tools_page_lists_all_catalog_tools():
    html = (_CONSOLE_DOCS / "tools.html").read_text(encoding="utf-8")
    catalog = catalog_from_snapshot(load_and_validate(build_seeded_store()))
    names = sorted(card.name for card in catalog.list())
    assert names, "工具目录为空"
    for name in names:
        assert name in html, f"工具清单页缺少工具 {name}"


def test_results_page_consumes_report_json():
    html = (_CONSOLE_DOCS / "results.html").read_text(encoding="utf-8")
    assert "report.json" in html
    assert "bdlh_runtime.evaluation.ab_eval" in html
