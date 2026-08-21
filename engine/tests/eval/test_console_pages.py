"""公开站点与真源同步守卫(七模块版,任务六)。

- 工具清单页(/engine/tools)必须覆盖工具目录全量工具名——目录增删工具页面未跟上即失败;
- 固定题库页(/experiment/cases)数据驱动:读 showcase-data 发布产物渲染,
  不再硬编码题号(题库↔页面同步由数据链路取代,ctx 用例入库并发布后自动出现);
- 实证结果页(/showcase/results)必须消费批次产物 report.json。
"""

from __future__ import annotations

import re
from pathlib import Path

from bdlh_runtime.registry import load_and_validate
from bdlh_runtime.tools.catalog import catalog_from_snapshot
from tests.registry.seeded_store import build_seeded_store

_WEB_PUBLIC = Path(__file__).resolve().parents[3] / "web" / "public"


def test_tools_page_lists_all_catalog_tools():
    html = (_WEB_PUBLIC / "engine" / "tools.html").read_text(encoding="utf-8")
    catalog = catalog_from_snapshot(load_and_validate(build_seeded_store()))
    names = sorted(card.name for card in catalog.list())
    assert names, "工具目录为空"
    for name in names:
        assert name in html, f"工具清单页缺少工具 {name}"


def test_cases_page_is_data_driven_not_hardcoded():
    """题库页去硬编码:读发布产物渲染,不得出现题号字面量(守卫对发布产物)。"""
    html = (_WEB_PUBLIC / "experiment" / "cases.html").read_text(encoding="utf-8")
    assert "showcase-data/index.json" in html, "题库页必须读发布索引"
    assert "showcase-data/batches/" in html, "题库页必须读批次报告"
    assert not re.search(r"(research|chat|know|miss|port|suit|coref|follow|ctx)-\d+", html), (
        "题库页不得硬编码题号表格(应读发布产物,ctx 用例入库后自动出现)"
    )


def test_results_page_consumes_report_json():
    html = (_WEB_PUBLIC / "showcase" / "results.html").read_text(encoding="utf-8")
    assert "report.json" in html
    assert "showcase-data" in html
