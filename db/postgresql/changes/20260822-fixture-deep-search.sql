-- 20260822-fixture-deep-search.sql
-- GT-2：为 ab-eval 冻结集补 research.deep_search 正例冻结行。
-- 背景：deep_search 此前无冻结行，运行时命中 unknown tool 失败桩；
-- 本脚本补一条 SUCCESS 最小深度研究返回（结论摘要 + 来源列表，与 seed 08 风格一致）。
-- 对现有数据：纯新增（INSERT 一行），不修改既有 18 行；
-- fixture_sets 已有 ('ab-eval', 1) 行，不重插。
-- 服务影响：无需停止 Data 或 Engine（data 服务按请求读库，新行即时可见）。
-- 回滚参考：DELETE FROM touchstone.fixture_tool_responses
--           WHERE fixture_set_id='ab-eval' AND call_key='research.deep_search';

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '15s';

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- arguments_hash / response_hash 为 NOT NULL，与 seed 08 相同的
-- 先放开、INSERT 后 UPDATE 回填、再恢复模式。
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN arguments_hash DROP NOT NULL;
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN response_hash DROP NOT NULL;

-- 基准键行（arguments '{}' 与既有基准键行一致；sequence 续 18）。
-- 幂等：数据行与登记行均 ON CONFLICT DO NOTHING，可安全重跑。
INSERT INTO touchstone.fixture_tool_responses
    (fixture_set_id, fixture_set_version, call_key, tool_name, arguments,
     response_status, response, observed_at, simulated_latency_ms, sequence)
VALUES
('ab-eval', 1, 'research.deep_search', 'research.deep_search', '{}',
 'SUCCESS',
 '{"question":"宁德时代投资价值综合评估","objective":"多源交叉验证基本面与估值","conclusion":"宁德时代为全球动力电池龙头，半年报营收同比增长稳健、roe 高于行业均值；固态电池技术取得突破但量产节奏存在不确定性；估值 pe_ttm 高于行业中位数，短期资金呈净流出。综合判断：基本面中性偏强，估值偏高，适合已持仓者继续持有、未持仓者等待估值回归。","sources":[{"title":"固态电池最新进展","url":"https://example.com/1"},{"title":"新能源行业分析","url":"https://example.com/2"},{"title":"宁德时代发布半年报","url":"https://example.com/3"}]}',
 '2026-08-19 14:32:00+08', 5, 18)
ON CONFLICT DO NOTHING;

UPDATE touchstone.fixture_tool_responses
SET arguments_hash = 'sha256:' || encode(digest(arguments::text, 'sha256'), 'hex'),
    response_hash  = 'sha256:' || encode(digest(response::text, 'sha256'), 'hex')
WHERE fixture_set_id = 'ab-eval' AND fixture_set_version = 1
  AND call_key = 'research.deep_search';

ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN arguments_hash SET NOT NULL;
ALTER TABLE touchstone.fixture_tool_responses ALTER COLUMN response_hash SET NOT NULL;

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('20260822-fixture-deep-search.sql', 'GT-2：ab-eval 冻结集补 research.deep_search SUCCESS 冻结行（结论摘要+来源列表）')
ON CONFLICT DO NOTHING;

COMMIT;
