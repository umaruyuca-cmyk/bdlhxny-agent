"""测试共享：A/B 评测冻结工具返回（与 db seed 08 同步）。

镜像 ``GET /internal/v1/tool-fixtures/ab-eval`` 的 payload 形状，供单测构建
``FrozenObservations``；与 seed SQL 的漂移由 ``test_frozen_fixture_sync`` 守卫。
"""

from __future__ import annotations

from typing import Any

# (call_key, tool_name, response)：行内容必须与 db/postgresql/setup/08-seed-tool-fixtures.sql 一致
FROZEN_RESPONSES: list[tuple[str, str, dict[str, Any]]] = [
    (
        "market.resolve_instrument",
        "market.resolve_instrument",
        {"symbol": "300750", "name": "宁德时代", "exchange": "SZSE", "industry": "电池"},
    ),
    (
        "market.get_realtime_quote",
        "market.get_realtime_quote",
        {"symbol": "300750", "name": "宁德时代", "price": 185.50, "change": -2.30, "pct_change": -1.22,
         "volume": 1234567, "timestamp": "2026-08-19 14:32:00"},
    ),
    (
        "market.get_valuation",
        "market.get_valuation",
        {"symbol": "300750", "pe_ttm": 28.5, "pb": 5.2, "pe_percentile": 0.65, "pb_percentile": 0.45},
    ),
    (
        "market.get_financial_statements",
        "market.get_financial_statements",
        {"symbol": "300750", "revenue_yoy": 0.153, "net_margin": 0.121, "roe": 0.187, "gross_margin": 0.221},
    ),
    (
        "market.get_historical_prices",
        "market.get_historical_prices",
        {"symbol": "300750", "prices": [
            {"date": "2026-08-18", "open": 187.0, "high": 188.5, "low": 184.2, "close": 185.5, "volume": 1234567},
            {"date": "2026-08-15", "open": 182.0, "high": 186.0, "low": 181.5, "close": 185.0, "volume": 987654},
        ]},
    ),
    (
        "market.get_industry_context",
        "market.get_industry_context",
        {"industry": "电池", "rank": 1, "market_share": 0.32, "industry_pe_median": 22.3},
    ),
    (
        "market.get_news",
        "market.get_news",
        {"items": [
            {"title": "宁德时代发布半年报", "source": "深交所", "time": "2026-08-18"},
            {"title": "固态电池技术突破", "source": "科技日报", "time": "2026-08-15"},
        ]},
    ),
    (
        "market.get_money_flow",
        "market.get_money_flow",
        {"net_inflow": -1234567.89, "main_force": "net_outflow", "super_large": -2345678.90},
    ),
    (
        "research.web_search",
        "research.web_search",
        {"results": [
            {"title": "固态电池最新进展", "url": "https://example.com/1", "snippet": "宁德时代固态电池取得突破性进展"},
            {"title": "新能源行业分析", "url": "https://example.com/2", "snippet": "2026年新能源电池行业持续增长"},
        ]},
    ),
    (
        "portfolio.get_current_positions",
        "portfolio.get_current_positions",
        {"positions": [
            {"symbol": "300750", "name": "宁德时代", "quantity": 200, "cost": 150.0, "weight": 0.18},
            {"symbol": "600519", "name": "贵州茅台", "quantity": 50, "cost": 1680.0, "weight": 0.22},
        ]},
    ),
    (
        "portfolio.get_account_snapshot",
        "portfolio.get_account_snapshot",
        {"cash": 50000, "total_assets": 87100, "market_value": 37100, "total_cost": 30000},
    ),
    (
        "portfolio.get_transaction_history",
        "portfolio.get_transaction_history",
        {"transactions": [
            {"date": "2026-07-15", "symbol": "300750", "action": "buy", "quantity": 100, "price": 150.0},
            {"date": "2026-06-20", "symbol": "600519", "action": "buy", "quantity": 50, "price": 1680.0},
        ]},
    ),
    (
        "portfolio.build_current_valuation",
        "portfolio.build_current_valuation",
        {"market_value": 37100, "total_cost": 30000, "pnl": 7100, "pnl_pct": 0.237},
    ),
    (
        "user.get_risk_profile",
        "user.get_risk_profile",
        {"risk_tolerance": "moderate", "risk_level": "R3", "description": "稳健型"},
    ),
    (
        "analysis.run_analysis",
        "analysis.run_analysis",
        {"score": 72, "rating": "中性偏强", "dimensions": {"technical": 78, "fundamental": 74, "valuation": 52,
                                                             "money_flow": 65, "sentiment": 71},
         "findings": ["技术面短期超买", "基本面营收增长稳健", "估值高于行业中位数"]},
    ),
    (
        "market.get_realtime_quote:600519",
        "market.get_realtime_quote",
        {"symbol": "600519", "name": "贵州茅台", "price": 1685.00, "change": 12.50, "pct_change": 0.75,
         "volume": 234567, "timestamp": "2026-08-19 14:32:00"},
    ),
    (
        "market.get_valuation:600519",
        "market.get_valuation",
        {"symbol": "600519", "pe_ttm": 32.1, "pb": 11.2, "pe_percentile": 0.72, "pb_percentile": 0.85},
    ),
    (
        "market.resolve_instrument:600519",
        "market.resolve_instrument",
        {"symbol": "600519", "name": "贵州茅台", "exchange": "SHSE", "industry": "白酒"},
    ),
    # GT-2 补录(changes/20260822-fixture-deep-search.sql,sequence 18):
    # deep_search 最小深度研究返回——结论摘要 + 来源列表。
    (
        "research.deep_search",
        "research.deep_search",
        {"question": "宁德时代投资价值综合评估", "objective": "多源交叉验证基本面与估值",
         "conclusion": "宁德时代为全球动力电池龙头，半年报营收同比增长稳健、roe 高于行业均值；"
                       "固态电池技术取得突破但量产节奏存在不确定性；估值 pe_ttm 高于行业中位数，"
                       "短期资金呈净流出。综合判断：基本面中性偏强，估值偏高，"
                       "适合已持仓者继续持有、未持仓者等待估值回归。",
         "sources": [
             {"title": "固态电池最新进展", "url": "https://example.com/1"},
             {"title": "新能源行业分析", "url": "https://example.com/2"},
             {"title": "宁德时代发布半年报", "url": "https://example.com/3"},
         ]},
    ),
]


def frozen_payload() -> dict[str, Any]:
    """构建与 data 服务 ``/internal/v1/tool-fixtures/ab-eval`` 同构的 payload。"""
    return {
        "fixtureSetId": "ab-eval",
        "fixtureSetVersion": 1,
        "responses": [
            {
                "call_key": call_key,
                "tool_name": tool_name,
                "response_status": "SUCCESS",
                "response": response,
            }
            for call_key, tool_name, response in FROZEN_RESPONSES
        ],
    }


# (call_key, tool_name, response_status, response):负例集行,
# 与 db/postgresql/changes/20260822-fixture-negative.sql 同步(顺序=sequence)。
# 组成:正例拷贝 11(部分成功场景)+ symbol 负例 24(8 工具×空/失败/超时)
# + 非 symbol FAILED 8(空/超时档在现行 call_key 语义下不可表达)。
NEGATIVE_RESPONSES: list[tuple[str, str, str, dict[str, Any]]] = [
    ("market.resolve_instrument", "market.resolve_instrument", "SUCCESS",
     {"symbol": "300750", "name": "宁德时代", "exchange": "SZSE", "industry": "电池"}),
    ("market.get_realtime_quote", "market.get_realtime_quote", "SUCCESS",
     {"symbol": "300750", "name": "宁德时代", "price": 185.50, "change": -2.30, "pct_change": -1.22,
      "volume": 1234567, "timestamp": "2026-08-19 14:32:00"}),
    ("market.get_valuation", "market.get_valuation", "SUCCESS",
     {"symbol": "300750", "pe_ttm": 28.5, "pb": 5.2, "pe_percentile": 0.65, "pb_percentile": 0.45}),
    ("market.get_financial_statements", "market.get_financial_statements", "SUCCESS",
     {"symbol": "300750", "revenue_yoy": 0.153, "net_margin": 0.121, "roe": 0.187, "gross_margin": 0.221}),
    ("market.get_historical_prices", "market.get_historical_prices", "SUCCESS",
     {"symbol": "300750", "prices": [
         {"date": "2026-08-18", "open": 187.0, "high": 188.5, "low": 184.2, "close": 185.5, "volume": 1234567},
         {"date": "2026-08-15", "open": 182.0, "high": 186.0, "low": 181.5, "close": 185.0, "volume": 987654},
     ]}),
    ("market.get_industry_context", "market.get_industry_context", "SUCCESS",
     {"industry": "电池", "rank": 1, "market_share": 0.32, "industry_pe_median": 22.3}),
    ("market.get_news", "market.get_news", "SUCCESS",
     {"items": [
         {"title": "宁德时代发布半年报", "source": "深交所", "time": "2026-08-18"},
         {"title": "固态电池技术突破", "source": "科技日报", "time": "2026-08-15"},
     ]}),
    ("market.get_money_flow", "market.get_money_flow", "SUCCESS",
     {"net_inflow": -1234567.89, "main_force": "net_outflow", "super_large": -2345678.90}),
    ("market.get_realtime_quote:600519", "market.get_realtime_quote", "SUCCESS",
     {"symbol": "600519", "name": "贵州茅台", "price": 1685.00, "change": 12.50, "pct_change": 0.75,
      "volume": 234567, "timestamp": "2026-08-19 14:32:00"}),
    ("market.get_valuation:600519", "market.get_valuation", "SUCCESS",
     {"symbol": "600519", "pe_ttm": 32.1, "pb": 11.2, "pe_percentile": 0.72, "pb_percentile": 0.85}),
    ("market.resolve_instrument:600519", "market.resolve_instrument", "SUCCESS",
     {"symbol": "600519", "name": "贵州茅台", "exchange": "SHSE", "industry": "白酒"}),
    ("market.resolve_instrument:000000", "market.resolve_instrument", "SUCCESS",
     {"symbol": "000000", "name": None, "exchange": None, "industry": None}),
    ("market.resolve_instrument:999999", "market.resolve_instrument", "ERROR",
     {"error": "symbol not found"}),
    ("market.resolve_instrument:888888", "market.resolve_instrument", "TIMEOUT",
     {"error": "resolve service timeout"}),
    ("market.get_realtime_quote:000000", "market.get_realtime_quote", "SUCCESS",
     {"symbol": "000000", "price": None, "change": None, "pct_change": None, "volume": None,
      "timestamp": "2026-08-19 14:32:00"}),
    ("market.get_realtime_quote:999999", "market.get_realtime_quote", "ERROR",
     {"error": "symbol not found"}),
    ("market.get_realtime_quote:888888", "market.get_realtime_quote", "TIMEOUT",
     {"error": "quote service timeout"}),
    ("market.get_valuation:000000", "market.get_valuation", "SUCCESS",
     {"symbol": "000000", "pe_ttm": None, "pb": None, "pe_percentile": None, "pb_percentile": None}),
    ("market.get_valuation:999999", "market.get_valuation", "ERROR",
     {"error": "symbol not found"}),
    ("market.get_valuation:888888", "market.get_valuation", "TIMEOUT",
     {"error": "valuation service timeout"}),
    ("market.get_financial_statements:000000", "market.get_financial_statements", "SUCCESS",
     {"symbol": "000000", "revenue_yoy": None, "net_margin": None, "roe": None, "gross_margin": None}),
    ("market.get_financial_statements:999999", "market.get_financial_statements", "ERROR",
     {"error": "symbol not found"}),
    ("market.get_financial_statements:888888", "market.get_financial_statements", "TIMEOUT",
     {"error": "filings service timeout"}),
    ("market.get_historical_prices:000000", "market.get_historical_prices", "SUCCESS",
     {"symbol": "000000", "prices": []}),
    ("market.get_historical_prices:999999", "market.get_historical_prices", "ERROR",
     {"error": "symbol not found"}),
    ("market.get_historical_prices:888888", "market.get_historical_prices", "TIMEOUT",
     {"error": "history service timeout"}),
    ("market.get_industry_context:000000", "market.get_industry_context", "SUCCESS",
     {"industry": None, "rank": None, "market_share": None, "industry_pe_median": None}),
    ("market.get_industry_context:999999", "market.get_industry_context", "ERROR",
     {"error": "symbol not found"}),
    ("market.get_industry_context:888888", "market.get_industry_context", "TIMEOUT",
     {"error": "industry service timeout"}),
    ("market.get_news:000000", "market.get_news", "SUCCESS", {"items": []}),
    ("market.get_news:999999", "market.get_news", "ERROR", {"error": "news source not found"}),
    ("market.get_news:888888", "market.get_news", "TIMEOUT", {"error": "news source timeout"}),
    ("market.get_money_flow:000000", "market.get_money_flow", "SUCCESS",
     {"net_inflow": None, "items": []}),
    ("market.get_money_flow:999999", "market.get_money_flow", "ERROR",
     {"error": "symbol not found"}),
    ("market.get_money_flow:888888", "market.get_money_flow", "TIMEOUT",
     {"error": "money flow service timeout"}),
    ("research.web_search", "research.web_search", "ERROR", {"error": "search backend unavailable"}),
    ("research.deep_search", "research.deep_search", "ERROR", {"error": "deep research quota exceeded"}),
    ("analysis.run_analysis", "analysis.run_analysis", "ERROR", {"error": "analysis engine unavailable"}),
    ("portfolio.get_current_positions", "portfolio.get_current_positions", "ERROR",
     {"error": "portfolio service unavailable"}),
    ("portfolio.get_account_snapshot", "portfolio.get_account_snapshot", "ERROR",
     {"error": "account service unavailable"}),
    ("portfolio.get_transaction_history", "portfolio.get_transaction_history", "ERROR",
     {"error": "transaction history unavailable"}),
    ("portfolio.build_current_valuation", "portfolio.build_current_valuation", "ERROR",
     {"error": "valuation builder unavailable"}),
    ("user.get_risk_profile", "user.get_risk_profile", "ERROR", {"error": "profile service unavailable"}),
]


def negative_payload() -> dict[str, Any]:
    """构建与 data 服务 ``/internal/v1/tool-fixtures/ab-eval-negative-v1`` 同构的 payload。"""
    return {
        "fixtureSetId": "ab-eval-negative-v1",
        "fixtureSetVersion": 1,
        "responses": [
            {
                "call_key": call_key,
                "tool_name": tool_name,
                "response_status": status,
                "response": response,
            }
            for call_key, tool_name, status, response in NEGATIVE_RESPONSES
        ],
    }
