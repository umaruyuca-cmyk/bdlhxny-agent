-- 20260822-fixture-negative.sql
-- GT-3：金融负例冻结集 ab-eval-negative-v1 + 负例用例 8 道(四类各 2)。
--
-- 覆盖表结论(见任务清单修订记录 2026-08-22(八)):ab-eval 16 工具仅有 SUCCESS
-- 正例,空结果/FAILED/TIMEOUT 三档缺口即本脚本写入范围。
-- 组成(43 行):
--   ① 正例拷贝 11 条:8 个 symbol 型 market 工具基准行 + 3 条 600519 覆盖行
--      (与 ab-eval 同内容,支撑部分成功场景的一 SUCCESS 一 FAILED 组合);
--   ② symbol 负例 24 条:8 个 market 工具 × 3 档覆盖键
--      (000000=空结果 SUCCESS 空内容 / 999999=FAILED / 888888=TIMEOUT);
--   ③ 非 symbol 工具 8 条:基准键 FAILED(覆盖键仅认 symbol 参数,空/超时档
--      在现行 call_key 语义下不可表达,取舍见修订记录)。
-- 对现有数据:纯新增;ab-eval 集不动。fixture_sets 新增一行。
-- 服务影响:无需停止 Data 或 Engine(data 服务按请求读库,新行即时可见)。
-- 回滚参考:DELETE FROM touchstone.fixture_tool_responses WHERE fixture_set_id='ab-eval-negative-v1';
--           DELETE FROM touchstone.fixture_sets WHERE id='ab-eval-negative-v1';
--           DELETE FROM touchstone.data_snapshots WHERE id LIKE 'neg-%';
--           DELETE FROM touchstone.case_steps WHERE case_id LIKE 'neg-%';
--           DELETE FROM touchstone.case_variants WHERE case_id LIKE 'neg-%';
--           DELETE FROM touchstone.case_versions WHERE case_id LIKE 'neg-%';
--           DELETE FROM touchstone.case_definitions WHERE id LIKE 'neg-%';
-- 幂等:INSERT 带 ON CONFLICT DO NOTHING,可安全重跑。

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ── 1. 冻结集登记 ──────────────────────────────────────────────────────

INSERT INTO touchstone.fixture_sets (id, version, title, fixture_type, source_hash, public)
VALUES ('ab-eval-negative-v1', 1, 'A/B 评测金融负例冻结返回(空结果/失败/超时)', 'STATIC',
        encode(digest('ab-eval negative tool fixtures v1', 'sha256'), 'hex'), false)
ON CONFLICT DO NOTHING;

-- arguments_hash / response_hash 为 NOT NULL,沿用 seed 08 的
-- 先放开、INSERT 后 UPDATE 回填、再恢复模式。
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN arguments_hash DROP NOT NULL;
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN response_hash DROP NOT NULL;

INSERT INTO touchstone.fixture_tool_responses
    (fixture_set_id, fixture_set_version, call_key, tool_name, arguments,
     response_status, response, observed_at, simulated_latency_ms, sequence)
VALUES
-- ① 正例拷贝(8 基准 + 3 覆盖,内容与 ab-eval 一致)
('ab-eval-negative-v1', 1, 'market.resolve_instrument', 'market.resolve_instrument', '{}',
 'SUCCESS', '{"symbol":"300750","name":"宁德时代","exchange":"SZSE","industry":"电池"}',
 '2026-08-19 14:32:00+08', 5, 0),
('ab-eval-negative-v1', 1, 'market.get_realtime_quote', 'market.get_realtime_quote', '{}',
 'SUCCESS', '{"symbol":"300750","name":"宁德时代","price":185.50,"change":-2.30,"pct_change":-1.22,"volume":1234567,"timestamp":"2026-08-19 14:32:00"}',
 '2026-08-19 14:32:00+08', 5, 1),
('ab-eval-negative-v1', 1, 'market.get_valuation', 'market.get_valuation', '{}',
 'SUCCESS', '{"symbol":"300750","pe_ttm":28.5,"pb":5.2,"pe_percentile":0.65,"pb_percentile":0.45}',
 '2026-08-19 14:32:00+08', 5, 2),
('ab-eval-negative-v1', 1, 'market.get_financial_statements', 'market.get_financial_statements', '{}',
 'SUCCESS', '{"symbol":"300750","revenue_yoy":0.153,"net_margin":0.121,"roe":0.187,"gross_margin":0.221}',
 '2026-08-19 14:32:00+08', 5, 3),
('ab-eval-negative-v1', 1, 'market.get_historical_prices', 'market.get_historical_prices', '{}',
 'SUCCESS', '{"symbol":"300750","prices":[{"date":"2026-08-18","open":187.0,"high":188.5,"low":184.2,"close":185.5,"volume":1234567},{"date":"2026-08-15","open":182.0,"high":186.0,"low":181.5,"close":185.0,"volume":987654}]}',
 '2026-08-19 14:32:00+08', 5, 4),
('ab-eval-negative-v1', 1, 'market.get_industry_context', 'market.get_industry_context', '{}',
 'SUCCESS', '{"industry":"电池","rank":1,"market_share":0.32,"industry_pe_median":22.3}',
 '2026-08-19 14:32:00+08', 5, 5),
('ab-eval-negative-v1', 1, 'market.get_news', 'market.get_news', '{}',
 'SUCCESS', '{"items":[{"title":"宁德时代发布半年报","source":"深交所","time":"2026-08-18"},{"title":"固态电池技术突破","source":"科技日报","time":"2026-08-15"}]}',
 '2026-08-19 14:32:00+08', 5, 6),
('ab-eval-negative-v1', 1, 'market.get_money_flow', 'market.get_money_flow', '{}',
 'SUCCESS', '{"net_inflow":-1234567.89,"main_force":"net_outflow","super_large":-2345678.90}',
 '2026-08-19 14:32:00+08', 5, 7),
('ab-eval-negative-v1', 1, 'market.get_realtime_quote:600519', 'market.get_realtime_quote', '{"symbol":"600519"}',
 'SUCCESS', '{"symbol":"600519","name":"贵州茅台","price":1685.00,"change":12.50,"pct_change":0.75,"volume":234567,"timestamp":"2026-08-19 14:32:00"}',
 '2026-08-19 14:32:00+08', 5, 8),
('ab-eval-negative-v1', 1, 'market.get_valuation:600519', 'market.get_valuation', '{"symbol":"600519"}',
 'SUCCESS', '{"symbol":"600519","pe_ttm":32.1,"pb":11.2,"pe_percentile":0.72,"pb_percentile":0.85}',
 '2026-08-19 14:32:00+08', 5, 9),
('ab-eval-negative-v1', 1, 'market.resolve_instrument:600519', 'market.resolve_instrument', '{"symbol":"600519"}',
 'SUCCESS', '{"symbol":"600519","name":"贵州茅台","exchange":"SHSE","industry":"白酒"}',
 '2026-08-19 14:32:00+08', 5, 10),
-- ② symbol 负例:market.resolve_instrument
('ab-eval-negative-v1', 1, 'market.resolve_instrument:000000', 'market.resolve_instrument', '{"symbol":"000000"}',
 'SUCCESS', '{"symbol":"000000","name":null,"exchange":null,"industry":null}',
 '2026-08-19 14:32:00+08', 5, 11),
('ab-eval-negative-v1', 1, 'market.resolve_instrument:999999', 'market.resolve_instrument', '{"symbol":"999999"}',
 'ERROR', '{"error":"symbol not found"}',
 '2026-08-19 14:32:00+08', 5, 12),
('ab-eval-negative-v1', 1, 'market.resolve_instrument:888888', 'market.resolve_instrument', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"resolve service timeout"}',
 '2026-08-19 14:32:00+08', 30000, 13),
-- market.get_realtime_quote
('ab-eval-negative-v1', 1, 'market.get_realtime_quote:000000', 'market.get_realtime_quote', '{"symbol":"000000"}',
 'SUCCESS', '{"symbol":"000000","price":null,"change":null,"pct_change":null,"volume":null,"timestamp":"2026-08-19 14:32:00"}',
 '2026-08-19 14:32:00+08', 5, 14),
('ab-eval-negative-v1', 1, 'market.get_realtime_quote:999999', 'market.get_realtime_quote', '{"symbol":"999999"}',
 'ERROR', '{"error":"symbol not found"}',
 '2026-08-19 14:32:00+08', 5, 15),
('ab-eval-negative-v1', 1, 'market.get_realtime_quote:888888', 'market.get_realtime_quote', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"quote service timeout"}',
 '2026-08-19 14:32:00+08', 30000, 16),
-- market.get_valuation
('ab-eval-negative-v1', 1, 'market.get_valuation:000000', 'market.get_valuation', '{"symbol":"000000"}',
 'SUCCESS', '{"symbol":"000000","pe_ttm":null,"pb":null,"pe_percentile":null,"pb_percentile":null}',
 '2026-08-19 14:32:00+08', 5, 17),
('ab-eval-negative-v1', 1, 'market.get_valuation:999999', 'market.get_valuation', '{"symbol":"999999"}',
 'ERROR', '{"error":"symbol not found"}',
 '2026-08-19 14:32:00+08', 5, 18),
('ab-eval-negative-v1', 1, 'market.get_valuation:888888', 'market.get_valuation', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"valuation service timeout"}',
 '2026-08-19 14:32:00+08', 30000, 19),
-- market.get_financial_statements
('ab-eval-negative-v1', 1, 'market.get_financial_statements:000000', 'market.get_financial_statements', '{"symbol":"000000"}',
 'SUCCESS', '{"symbol":"000000","revenue_yoy":null,"net_margin":null,"roe":null,"gross_margin":null}',
 '2026-08-19 14:32:00+08', 5, 20),
('ab-eval-negative-v1', 1, 'market.get_financial_statements:999999', 'market.get_financial_statements', '{"symbol":"999999"}',
 'ERROR', '{"error":"symbol not found"}',
 '2026-08-19 14:32:00+08', 5, 21),
('ab-eval-negative-v1', 1, 'market.get_financial_statements:888888', 'market.get_financial_statements', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"filings service timeout"}',
 '2026-08-19 14:32:00+08', 30000, 22),
-- market.get_historical_prices
('ab-eval-negative-v1', 1, 'market.get_historical_prices:000000', 'market.get_historical_prices', '{"symbol":"000000"}',
 'SUCCESS', '{"symbol":"000000","prices":[]}',
 '2026-08-19 14:32:00+08', 5, 23),
('ab-eval-negative-v1', 1, 'market.get_historical_prices:999999', 'market.get_historical_prices', '{"symbol":"999999"}',
 'ERROR', '{"error":"symbol not found"}',
 '2026-08-19 14:32:00+08', 5, 24),
('ab-eval-negative-v1', 1, 'market.get_historical_prices:888888', 'market.get_historical_prices', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"history service timeout"}',
 '2026-08-19 14:32:00+08', 30000, 25),
-- market.get_industry_context
('ab-eval-negative-v1', 1, 'market.get_industry_context:000000', 'market.get_industry_context', '{"symbol":"000000"}',
 'SUCCESS', '{"industry":null,"rank":null,"market_share":null,"industry_pe_median":null}',
 '2026-08-19 14:32:00+08', 5, 26),
('ab-eval-negative-v1', 1, 'market.get_industry_context:999999', 'market.get_industry_context', '{"symbol":"999999"}',
 'ERROR', '{"error":"symbol not found"}',
 '2026-08-19 14:32:00+08', 5, 27),
('ab-eval-negative-v1', 1, 'market.get_industry_context:888888', 'market.get_industry_context', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"industry service timeout"}',
 '2026-08-19 14:32:00+08', 30000, 28),
-- market.get_news
('ab-eval-negative-v1', 1, 'market.get_news:000000', 'market.get_news', '{"symbol":"000000"}',
 'SUCCESS', '{"items":[]}',
 '2026-08-19 14:32:00+08', 5, 29),
('ab-eval-negative-v1', 1, 'market.get_news:999999', 'market.get_news', '{"symbol":"999999"}',
 'ERROR', '{"error":"news source not found"}',
 '2026-08-19 14:32:00+08', 5, 30),
('ab-eval-negative-v1', 1, 'market.get_news:888888', 'market.get_news', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"news source timeout"}',
 '2026-08-19 14:32:00+08', 30000, 31),
-- market.get_money_flow
('ab-eval-negative-v1', 1, 'market.get_money_flow:000000', 'market.get_money_flow', '{"symbol":"000000"}',
 'SUCCESS', '{"net_inflow":null,"items":[]}',
 '2026-08-19 14:32:00+08', 5, 32),
('ab-eval-negative-v1', 1, 'market.get_money_flow:999999', 'market.get_money_flow', '{"symbol":"999999"}',
 'ERROR', '{"error":"symbol not found"}',
 '2026-08-19 14:32:00+08', 5, 33),
('ab-eval-negative-v1', 1, 'market.get_money_flow:888888', 'market.get_money_flow', '{"symbol":"888888"}',
 'TIMEOUT', '{"error":"money flow service timeout"}',
 '2026-08-19 14:32:00+08', 30000, 34),
-- ③ 非 symbol 工具:基准键 FAILED(空/超时档不可表达,取舍见修订记录)
('ab-eval-negative-v1', 1, 'research.web_search', 'research.web_search', '{}',
 'ERROR', '{"error":"search backend unavailable"}',
 '2026-08-19 14:32:00+08', 5, 35),
('ab-eval-negative-v1', 1, 'research.deep_search', 'research.deep_search', '{}',
 'ERROR', '{"error":"deep research quota exceeded"}',
 '2026-08-19 14:32:00+08', 5, 36),
('ab-eval-negative-v1', 1, 'analysis.run_analysis', 'analysis.run_analysis', '{}',
 'ERROR', '{"error":"analysis engine unavailable"}',
 '2026-08-19 14:32:00+08', 5, 37),
('ab-eval-negative-v1', 1, 'portfolio.get_current_positions', 'portfolio.get_current_positions', '{}',
 'ERROR', '{"error":"portfolio service unavailable"}',
 '2026-08-19 14:32:00+08', 5, 38),
('ab-eval-negative-v1', 1, 'portfolio.get_account_snapshot', 'portfolio.get_account_snapshot', '{}',
 'ERROR', '{"error":"account service unavailable"}',
 '2026-08-19 14:32:00+08', 5, 39),
('ab-eval-negative-v1', 1, 'portfolio.get_transaction_history', 'portfolio.get_transaction_history', '{}',
 'ERROR', '{"error":"transaction history unavailable"}',
 '2026-08-19 14:32:00+08', 5, 40),
('ab-eval-negative-v1', 1, 'portfolio.build_current_valuation', 'portfolio.build_current_valuation', '{}',
 'ERROR', '{"error":"valuation builder unavailable"}',
 '2026-08-19 14:32:00+08', 5, 41),
('ab-eval-negative-v1', 1, 'user.get_risk_profile', 'user.get_risk_profile', '{}',
 'ERROR', '{"error":"profile service unavailable"}',
 '2026-08-19 14:32:00+08', 5, 42);

UPDATE touchstone.fixture_tool_responses
SET arguments_hash = 'sha256:' || encode(digest(arguments::text, 'sha256'), 'hex'),
    response_hash  = 'sha256:' || encode(digest(response::text, 'sha256'), 'hex')
WHERE fixture_set_id = 'ab-eval-negative-v1' AND fixture_set_version = 1;

ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN arguments_hash SET NOT NULL;
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN response_hash SET NOT NULL;

-- ── 2. 负例用例(四类各 2 道;expected_behavior 供 GT-7 判官,v1 不消费) ──

INSERT INTO touchstone.case_definitions (id, title, current_version) VALUES
('neg-empty-01',   '负例·空结果:资金流查询', 1),
('neg-empty-02',   '负例·空结果:新闻查询', 1),
('neg-fail-01',    '负例·失败:行情查询', 1),
('neg-fail-02',    '负例·失败:财报查询', 1),
('neg-timeout-01', '负例·超时:新闻查询', 1),
('neg-timeout-02', '负例·超时:行情查询', 1),
('neg-partial-01', '负例·部分成功:估值对比', 1),
('neg-partial-02', '负例·部分成功:行情对比', 1)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.case_versions
    (case_id, version, message, scene, authenticated, allowed_tools,
     context_profile, token_budget, expected_checks, public)
VALUES
('neg-empty-01', 1, '查一下 000000 的资金流', 'market', false,
 '["market.get_money_flow"]', 'default', 8192,
 '{"category":"负例·空结果","expected_tools":["market.get_money_flow"],"expected_behavior":"report_empty"}', true),
('neg-empty-02', 1, '000000 最近有什么新闻', 'market', false,
 '["market.get_news"]', 'default', 8192,
 '{"category":"负例·空结果","expected_tools":["market.get_news"],"expected_behavior":"report_empty"}', true),
('neg-fail-01', 1, '999999 现在什么价', 'market', false,
 '["market.get_realtime_quote"]', 'default', 8192,
 '{"category":"负例·失败","expected_tools":["market.get_realtime_quote"],"expected_behavior":"report_failure"}', true),
('neg-fail-02', 1, '999999 的财报怎么样', 'market', false,
 '["market.get_financial_statements"]', 'default', 8192,
 '{"category":"负例·失败","expected_tools":["market.get_financial_statements"],"expected_behavior":"report_failure"}', true),
('neg-timeout-01', 1, '888888 最近有什么新闻', 'market', false,
 '["market.get_news"]', 'default', 8192,
 '{"category":"负例·超时","expected_tools":["market.get_news"],"expected_behavior":"report_timeout"}', true),
('neg-timeout-02', 1, '888888 现在什么价', 'market', false,
 '["market.get_realtime_quote"]', 'default', 8192,
 '{"category":"负例·超时","expected_tools":["market.get_realtime_quote"],"expected_behavior":"report_timeout"}', true),
('neg-partial-01', 1, '对比 300750 和 999999 的估值', 'market', false,
 '["market.get_valuation"]', 'default', 8192,
 '{"category":"负例·部分成功","expected_tools":["market.get_valuation"],"expected_behavior":"report_partial_failure"}', true),
('neg-partial-02', 1, '对比 300750 和 999999 的最新价', 'market', false,
 '["market.get_realtime_quote"]', 'default', 8192,
 '{"category":"负例·部分成功","expected_tools":["market.get_realtime_quote"],"expected_behavior":"report_partial_failure"}', true)
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.case_variants
    (case_id, case_version, variant_id, title, context_strategy, token_budget, data_fixture, public)
SELECT definitions.id, 1, 'default', '默认固定数据', 'budgeted',
       versions.token_budget,
       jsonb_build_object('fixture_id', definitions.id || '-fixture-v1'),
       true
FROM touchstone.case_definitions definitions
JOIN touchstone.case_versions versions
  ON versions.case_id = definitions.id AND versions.version = definitions.current_version
WHERE definitions.id LIKE 'neg-%'
ON CONFLICT DO NOTHING;

INSERT INTO touchstone.data_snapshots
    (id, case_id, case_version, variant_id, fixture_version, content, source_hash)
SELECT variants.case_id || ':fixture-v1', variants.case_id, variants.case_version,
       variants.variant_id, 'v1', variants.data_fixture,
       'sha256:' || encode(digest(variants.data_fixture::text, 'sha256'), 'hex')
FROM touchstone.case_variants variants
WHERE variants.case_id LIKE 'neg-%'
ON CONFLICT (id) DO NOTHING;

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('20260822-fixture-negative.sql',
        'GT-3:金融负例冻结集 ab-eval-negative-v1(43 行:正例拷贝11+symbol负例24+非symbol FAILED8)与负例用例 8 道(空结果/失败/超时/部分成功 各2)')
ON CONFLICT DO NOTHING;

COMMIT;

-- 执行后确认:
--   SELECT count(*) FROM touchstone.fixture_tool_responses
--     WHERE fixture_set_id='ab-eval-negative-v1';                    -- 应 43
--   SELECT response_status, count(*) FROM touchstone.fixture_tool_responses
--     WHERE fixture_set_id='ab-eval-negative-v1' GROUP BY 1;         -- SUCCESS 19 / FAILED 16 / TIMEOUT 8
--   SELECT count(*) FROM touchstone.case_definitions WHERE id LIKE 'neg-%';  -- 应 8
