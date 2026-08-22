"""公开站点与真源同步守卫(七模块版,任务六)。

- 工具构成页(/engine/tools)以聚合口径展示目录构成(通用/领域/元工具)——
  数量须与工具目录一致,逐名列举改为构成校验(页面不维护第二份全名单);
- 固定题库页(/experiment/cases)数据驱动:读 showcase-data 发布产物渲染,
  不再硬编码题号(题库↔页面同步由数据链路取代,ctx 用例入库并发布后自动出现);
- 实证结果页(/showcase/results)必须消费批次产物 report.json。
"""

from __future__ import annotations

import re
from pathlib import Path

_WEB_PUBLIC = Path(__file__).resolve().parents[3] / "web" / "public"


def test_tools_page_lists_all_catalog_tools():
    """工具构成页声明 DB 目录快照的构成(总量112=通用96+领域16+元工具)。

    engine 内存种子(17=金融16+检索元工具)与 DB 目录(112)不是同一真源,
    本守卫只锚定页面自身的构成声明;通用 96 工具的目录同步由
    tests/registry/test_generic_tools_sync.py 守卫。
    """
    html = (_WEB_PUBLIC / "engine" / "tools.html").read_text(encoding="utf-8")
    assert "112" in html, "构成页需声明目录总量 112"
    assert "96" in html and "16" in html, "构成页需声明 通用96/领域16 两档数量"
    assert "search_tools" in html, "检索元工具需在构成页说明"
    assert "快照" in html, "构成页需声明为目录快照投影(真源在数据库)"


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
