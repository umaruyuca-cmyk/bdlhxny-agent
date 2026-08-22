"""GT-6 通用工具目录同步守卫。

``db/postgresql/changes/20260822-generic-mock-tools.sql`` 是 96 个通用 Mock 工具
的唯一真源;``tests/registry/generic_tools_manifest.json`` 是测试镜像
(名字集合 + 写入标注)。两者漂移即失败。金融 16 工具(init.sql 种子)不在此脚本
范围内,不得被触碰。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_SQL = _REPO / "db" / "postgresql" / "changes" / "20260822-generic-mock-tools.sql"
_MANIFEST = Path(__file__).resolve().parent / "generic_tools_manifest.json"

FINANCIAL_16 = frozenset(
    {
        "market.resolve_instrument",
        "market.get_realtime_quote",
        "market.get_historical_prices",
        "market.get_financial_statements",
        "market.get_valuation",
        "market.get_industry_context",
        "market.get_money_flow",
        "market.get_news",
        "research.web_search",
        "research.deep_search",
        "analysis.run_analysis",
        "portfolio.get_current_positions",
        "portfolio.get_account_snapshot",
        "portfolio.get_transaction_history",
        "portfolio.build_current_valuation",
        "user.get_risk_profile",
    }
)

# 能力行段的行格式(生成器产物,字段顺序固定):
# (name, desc, domain, adapter, read_only, auth, required_args, '[]', timeout,
#  enabled, operations, toolsets, side_effect, requires_confirmation, risk_level)
_ROW = re.compile(
    r"^\('([a-z_.]+)', .*?', true, (true|false),\n"
    r" .*?, '\[\]', 20, true,\n"
    r" .*?, .*?, '(none|write|external_action)', (true|false), '(low|medium|high)'\)",
    re.MULTILINE,
)


def _manifest() -> dict:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def _capability_section() -> str:
    text = _SQL.read_text(encoding="utf-8")
    start = text.index("INSERT INTO touchstone.tool_capabilities")
    return text[start : text.index(";", start)]


def _sql_rows() -> list[tuple[str, str, str, str]]:
    """(name, side_effect, requires_confirmation, risk_level),按 SQL 顺序。"""
    return [(m.group(1), m.group(3), m.group(4), m.group(5)) for m in _ROW.finditer(_capability_section())]


def test_generic_tool_names_match_manifest():
    manifest = _manifest()
    sql_names = [row[0] for row in _sql_rows()]
    assert len(sql_names) == 96, f"能力行应 96,实际 {len(sql_names)}"
    assert sql_names == [tool["name"] for tool in manifest["tools"]], "96 工具名单与镜像清单不一致(含顺序)"


def test_write_annotations_match_manifest():
    """写入/高风险标注(评测轴三列)与镜像逐行一致——判官 GT-7 的数据基础。"""
    manifest = _manifest()
    sql_rows = _sql_rows()
    for (name, side, conf, risk), tool in zip(sql_rows, manifest["tools"], strict=True):
        assert tool["name"] == name
        assert tool["side_effect"] == side, f"{name} side_effect 漂移"
        assert tool["requires_confirmation"] == (conf == "true"), f"{name} requires_confirmation 漂移"
        assert tool["risk_level"] == risk, f"{name} risk_level 漂移"


def test_all_generic_tools_are_read_only_and_enabled():
    """治理轴不动:96 行全部匹配 read_only=true + enabled=true 的严格行式
    (写入性由 side_effect 评测轴表达,见行式正则中的字面量 true)。"""
    rows = _sql_rows()
    assert len(rows) == 96, "能力行段应全部匹配严格行式(read_only/enabled 恒 true)"


def test_financial_16_untouched_by_generic_script():
    """金融 16 行不动:通用脚本的能力行与金融名单零交集,且无 UPDATE/DELETE。"""
    sql_names = {row[0] for row in _sql_rows()}
    assert not sql_names & FINANCIAL_16
    text = _SQL.read_text(encoding="utf-8")
    assert not re.search(r"UPDATE\s+touchstone\.tool_capabilities", text), "通用脚本不得回写能力表"
    assert not re.search(r"DELETE\s+FROM\s+touchstone\.tool_capabilities", text), "通用脚本不得删除能力行"


def test_fixture_sets_cover_all_96_tools():
    """正例集 mock-eval-v1 覆盖全部 96 工具;负例集覆盖每个方向至少一档。"""
    text = _SQL.read_text(encoding="utf-8")
    positive = re.findall(r"\('mock-eval-v1', 1, '([a-z_.]+)'", text)
    manifest_names = [tool["name"] for tool in _manifest()["tools"]]
    assert sorted(positive) == sorted(manifest_names), "mock-eval-v1 应逐工具覆盖 96 名"
    assert len(positive) == 96 and len(set(positive)) == 96
    negative = re.findall(r"\('mock-eval-negative-v1', 1, '([a-z_.]+)'", text)
    # 负例代表性:每方向(工具首个域段之外的 toolset 维度)至少 2 行
    assert len(negative) >= 38, f"负例集应 ≥38 行(19 方向×2),实际 {len(negative)}"
    status_pattern = re.compile(
        r"\('mock-eval-negative-v1', 1, '[a-z_.]+', '[a-z_.]+', '\{\}',\n '(SUCCESS|ERROR|TIMEOUT)'"
    )
    statuses = status_pattern.findall(text)
    assert {"SUCCESS", "ERROR", "TIMEOUT"} <= set(statuses), "负例集应同时含空结果(SUCCESS 空内容)/ERROR/TIMEOUT 档"


def test_operations_registered_but_not_runtime_allowed():
    """8 个新操作证仅登记:不进代码侧 RUNTIME_ALLOWED_OPERATIONS(defaults.py 不动)。"""
    from bdlh_runtime.registry.defaults import DEFAULT_RUNTIME_ALLOWED_OPERATIONS

    text = _SQL.read_text(encoding="utf-8")
    start = text.index("INSERT INTO touchstone.tool_operations")
    section = text[start : text.index(";", start)]
    new_ops = re.findall(r"^\('([A-Z_]+)',", section, re.MULTILINE)
    assert len(new_ops) == 8
    assert set(new_ops) >= {
        "WRITE_COMMUNICATION",
        "WRITE_SCHEDULE",
        "WRITE_FILE",
        "WRITE_DEVICE",
        "EXECUTE_CODE",
        "WRITE_CART",
    }
    assert not set(new_ops) & set(DEFAULT_RUNTIME_ALLOWED_OPERATIONS), "新操作证不得进入运行允许集"
