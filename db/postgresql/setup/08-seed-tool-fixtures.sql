BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- A/B 评测冻结工具数据（唯一真源）：三组对照共用，隔离工具执行质量差异。
-- call_key 规则：基准返回为工具名；标的覆盖为「工具名:标的代码」。
-- engine 经 data 服务 /internal/v1/tool-fixtures/ab-eval 读取。

INSERT INTO touchstone.fixture_sets (id, version, title, fixture_type, source_hash, public)
VALUES ('ab-eval', 1, 'A/B 评测冻结工具返回', 'STATIC',
        encode(digest('ab-eval frozen tool fixtures v1', 'sha256'), 'hex'), false);

INSERT INTO touchstone.fixture_tool_responses
    (fixture_set_id, fixture_set_version, call_key, tool_name, arguments,
     response_status, response, observed_at, simulated_latency_ms, sequence)
VALUES
('ab-eval', 1, 'market.resolve_instrument', 'market.resolve_instrument', '{}',
 'SUCCESS', '{"symbol":"300750","name":"宁德时代","exchange":"SZSE","industry":"电池"}',
 '2026-08-19 14:32:00+08', 5, 0),
('ab-eval', 1, 'market.get_realtime_quote', 'market.get_realtime_quote', '{}',
 'SUCCESS', '{"symbol":"300750","name":"宁德时代","price":185.50,"change":-2.30,"pct_change":-1.22,"volume":1234567,"timestamp":"2026-08-19 14:32:00"}',
 '2026-08-19 14:32:00+08', 5, 1),
('ab-eval', 1, 'market.get_valuation', 'market.get_valuation', '{}',
 'SUCCESS', '{"symbol":"300750","pe_ttm":28.5,"pb":5.2,"pe_percentile":0.65,"pb_percentile":0.45}',
 '2026-08-19 14:32:00+08', 5, 2),
('ab-eval', 1, 'market.get_financial_statements', 'market.get_financial_statements', '{}',
 'SUCCESS', '{"symbol":"300750","revenue_yoy":0.153,"net_margin":0.121,"roe":0.187,"gross_margin":0.221}',
 '2026-08-19 14:32:00+08', 5, 3),
('ab-eval', 1, 'market.get_historical_prices', 'market.get_historical_prices', '{}',
 'SUCCESS', '{"symbol":"300750","prices":[{"date":"2026-08-18","open":187.0,"high":188.5,"low":184.2,"close":185.5,"volume":1234567},{"date":"2026-08-15","open":182.0,"high":186.0,"low":181.5,"close":185.0,"volume":987654}]}',
 '2026-08-19 14:32:00+08', 5, 4),
('ab-eval', 1, 'market.get_industry_context', 'market.get_industry_context', '{}',
 'SUCCESS', '{"industry":"电池","rank":1,"market_share":0.32,"industry_pe_median":22.3}',
 '2026-08-19 14:32:00+08', 5, 5),
('ab-eval', 1, 'market.get_news', 'market.get_news', '{}',
 'SUCCESS', '{"items":[{"title":"宁德时代发布半年报","source":"深交所","time":"2026-08-18"},{"title":"固态电池技术突破","source":"科技日报","time":"2026-08-15"}]}',
 '2026-08-19 14:32:00+08', 5, 6),
('ab-eval', 1, 'market.get_money_flow', 'market.get_money_flow', '{}',
 'SUCCESS', '{"net_inflow":-1234567.89,"main_force":"net_outflow","super_large":-2345678.90}',
 '2026-08-19 14:32:00+08', 5, 7),
('ab-eval', 1, 'research.web_search', 'research.web_search', '{}',
 'SUCCESS', '{"results":[{"title":"固态电池最新进展","url":"https://example.com/1","snippet":"宁德时代固态电池取得突破性进展"},{"title":"新能源行业分析","url":"https://example.com/2","snippet":"2026年新能源电池行业持续增长"}]}',
 '2026-08-19 14:32:00+08', 5, 8),
('ab-eval', 1, 'portfolio.get_current_positions', 'portfolio.get_current_positions', '{}',
 'SUCCESS', '{"positions":[{"symbol":"300750","name":"宁德时代","quantity":200,"cost":150.0,"weight":0.18},{"symbol":"600519","name":"贵州茅台","quantity":50,"cost":1680.0,"weight":0.22}]}',
 '2026-08-19 14:32:00+08', 5, 9),
('ab-eval', 1, 'portfolio.get_account_snapshot', 'portfolio.get_account_snapshot', '{}',
 'SUCCESS', '{"cash":50000,"total_assets":87100,"market_value":37100,"total_cost":30000}',
 '2026-08-19 14:32:00+08', 5, 10),
('ab-eval', 1, 'portfolio.get_transaction_history', 'portfolio.get_transaction_history', '{}',
 'SUCCESS', '{"transactions":[{"date":"2026-07-15","symbol":"300750","action":"buy","quantity":100,"price":150.0},{"date":"2026-06-20","symbol":"600519","action":"buy","quantity":50,"price":1680.0}]}',
 '2026-08-19 14:32:00+08', 5, 11),
('ab-eval', 1, 'portfolio.build_current_valuation', 'portfolio.build_current_valuation', '{}',
 'SUCCESS', '{"market_value":37100,"total_cost":30000,"pnl":7100,"pnl_pct":0.237}',
 '2026-08-19 14:32:00+08', 5, 12),
('ab-eval', 1, 'user.get_risk_profile', 'user.get_risk_profile', '{}',
 'SUCCESS', '{"risk_tolerance":"moderate","risk_level":"R3","description":"稳健型"}',
 '2026-08-19 14:32:00+08', 5, 13),
('ab-eval', 1, 'analysis.run_analysis', 'analysis.run_analysis', '{}',
 'SUCCESS', '{"score":72,"rating":"中性偏强","dimensions":{"technical":78,"fundamental":74,"valuation":52,"money_flow":65,"sentiment":71},"findings":["技术面短期超买","基本面营收增长稳健","估值高于行业中位数"]}',
 '2026-08-19 14:32:00+08', 5, 14),
('ab-eval', 1, 'market.get_realtime_quote:600519', 'market.get_realtime_quote', '{"symbol":"600519"}',
 'SUCCESS', '{"symbol":"600519","name":"贵州茅台","price":1685.00,"change":12.50,"pct_change":0.75,"volume":234567,"timestamp":"2026-08-19 14:32:00"}',
 '2026-08-19 14:32:00+08', 5, 15),
('ab-eval', 1, 'market.get_valuation:600519', 'market.get_valuation', '{"symbol":"600519"}',
 'SUCCESS', '{"symbol":"600519","pe_ttm":32.1,"pb":11.2,"pe_percentile":0.72,"pb_percentile":0.85}',
 '2026-08-19 14:32:00+08', 5, 16),
('ab-eval', 1, 'market.resolve_instrument:600519', 'market.resolve_instrument', '{"symbol":"600519"}',
 'SUCCESS', '{"symbol":"600519","name":"贵州茅台","exchange":"SHSE","industry":"白酒"}',
 '2026-08-19 14:32:00+08', 5, 17);

-- 参数与响应 hash 由数据库对最终存储值统一派生（sha256:<hex> 全局约定）。
UPDATE touchstone.fixture_tool_responses
SET arguments_hash = 'sha256:' || encode(digest(arguments::text, 'sha256'), 'hex'),
    response_hash  = 'sha256:' || encode(digest(response::text, 'sha256'), 'hex')
WHERE fixture_set_id = 'ab-eval' AND fixture_set_version = 1;

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('08-seed-tool-fixtures.sql', '写入 A/B 评测冻结工具返回（ab-eval 数据集，18 条固定返回）');

COMMIT;
