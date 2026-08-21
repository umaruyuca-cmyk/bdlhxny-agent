BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

-- 工具目录（唯一真源）：操作证、工具集、工具能力与技能。
-- engine 经 data 服务 /internal/v1/tool-catalog 读取，不再维护 Python 种子。

CREATE TABLE touchstone.tool_operations (
    code         VARCHAR(100) PRIMARY KEY,
    description  VARCHAR(500) NOT NULL
);

CREATE TABLE touchstone.toolsets (
    name         VARCHAR(100) PRIMARY KEY,
    description  VARCHAR(500) NOT NULL
);

CREATE TABLE touchstone.tool_capabilities (
    name                        VARCHAR(200) PRIMARY KEY,
    description                 VARCHAR(1000) NOT NULL,
    domain                      VARCHAR(100) NOT NULL,
    adapter                     VARCHAR(20) NOT NULL,
    read_only                   BOOLEAN NOT NULL DEFAULT TRUE,
    requires_authenticated_user BOOLEAN NOT NULL DEFAULT FALSE,
    required_arguments          JSONB NOT NULL DEFAULT '[]'::jsonb,
    depends_on                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    timeout_seconds             INTEGER NOT NULL DEFAULT 20,
    enabled                     BOOLEAN NOT NULL DEFAULT TRUE,
    operations                  JSONB NOT NULL DEFAULT '[]'::jsonb,
    toolsets                    JSONB NOT NULL DEFAULT '[]'::jsonb,
    CONSTRAINT tool_capability_adapter_valid CHECK (
        adapter IN ('mcp', 'java', 'web', 'local')
    ),
    CONSTRAINT tool_capability_timeout_valid CHECK (timeout_seconds > 0)
);

CREATE TABLE touchstone.tool_skills (
    skill_id       VARCHAR(100) PRIMARY KEY,
    skill_version  VARCHAR(50) NOT NULL,
    domain         VARCHAR(100) NOT NULL,
    status         VARCHAR(30) NOT NULL,
    enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT tool_skill_status_valid CHECK (
        status IN ('CURRENT', 'FOUNDATION', 'EXPERIMENTAL')
    )
);

CREATE TABLE touchstone.tool_skill_operations (
    skill_id  VARCHAR(100) NOT NULL
              REFERENCES touchstone.tool_skills(skill_id) ON DELETE CASCADE,
    code      VARCHAR(100) NOT NULL REFERENCES touchstone.tool_operations(code),
    required  BOOLEAN NOT NULL,
    PRIMARY KEY (skill_id, code)
);

CREATE TABLE touchstone.tool_skill_capabilities (
    skill_id    VARCHAR(100) NOT NULL
                REFERENCES touchstone.tool_skills(skill_id) ON DELETE CASCADE,
    capability  VARCHAR(200) NOT NULL REFERENCES touchstone.tool_capabilities(name),
    required    BOOLEAN NOT NULL,
    PRIMARY KEY (skill_id, capability)
);

INSERT INTO touchstone.tool_operations (code, description) VALUES
('READ_MARKET_DATA', '读取公开市场数据'),
('READ_PUBLIC_RESEARCH', '读取外部公开研究资料'),
('READ_PORTFOLIO', '读取用户持仓与账户'),
('READ_PROFILE', '读取用户风险画像'),
('READ_FINANCIAL_GOALS', '读取用户财务目标'),
('RUN_ANALYSIS', '执行确定性金融分析'),
('PROPOSE_TASK', '提议持续观察任务');

INSERT INTO touchstone.toolsets (name, description) VALUES
('market_read', '读取标的、行情、历史价格和资金流数据'),
('fundamental_read', '读取财务报表、估值和行业背景数据'),
('news_read', '读取结构化新闻和外部公开资料'),
('portfolio_read', '只读访问当前用户持仓、账户和交易历史'),
('financial_profile_read', '只读访问当前用户风险画像和金融档案'),
('planning_compute', '对标准化数据执行确定性金融计算');

-- (name, description, adapter, auth, required_arguments, depends_on, operations, toolsets)
INSERT INTO touchstone.tool_capabilities
    (name, description, domain, adapter, requires_authenticated_user,
     required_arguments, depends_on, operations, toolsets)
VALUES
('market.resolve_instrument', '把名称或简称解析为标准标的', 'market', 'mcp', false,
 '["symbol"]', '[]', '["READ_MARKET_DATA"]', '["market_read"]'),
('market.get_realtime_quote', '查询标的最新行情', 'market', 'mcp', false,
 '["symbol"]', '["market.resolve_instrument"]', '["READ_MARKET_DATA"]', '["market_read"]'),
('market.get_historical_prices', '查询标的 Historical OHLCV 序列', 'market', 'mcp', false,
 '["symbol","lookback_days"]', '["market.resolve_instrument"]', '["READ_MARKET_DATA"]', '["market_read"]'),
('market.get_financial_statements', '查询标的标准化财务报表', 'market', 'mcp', false,
 '["symbol"]', '["market.resolve_instrument"]', '["READ_MARKET_DATA"]', '["fundamental_read"]'),
('market.get_valuation', '查询标的估值指标', 'market', 'mcp', false,
 '["symbol"]', '["market.resolve_instrument"]', '["READ_MARKET_DATA"]', '["fundamental_read"]'),
('market.get_industry_context', '查询标的所属行业与背景', 'market', 'mcp', false,
 '["symbol"]', '["market.resolve_instrument"]', '["READ_MARKET_DATA"]', '["fundamental_read"]'),
('market.get_money_flow', '查询标的资金流向', 'market', 'mcp', false,
 '["symbol"]', '["market.resolve_instrument"]', '["READ_MARKET_DATA"]', '["market_read"]'),
('market.get_news', '查询标的结构化新闻', 'market', 'mcp', false,
 '["symbol"]', '["market.resolve_instrument"]', '["READ_MARKET_DATA"]', '["news_read"]'),
('research.web_search', '检索外部公开资料并带来源返回', 'research', 'web', false,
 '["query"]', '[]', '["READ_PUBLIC_RESEARCH"]', '["news_read"]'),
('research.deep_search', '深度研究：多轮拆题检索与压缩（premium）', 'research', 'local', false,
 '["question","objective"]', '[]', '["READ_PUBLIC_RESEARCH"]', '["news_read"]'),
('analysis.run_analysis', '对标准化数据执行确定性金融分析', 'analysis', 'local', false,
 '[]', '[]', '["RUN_ANALYSIS"]', '["planning_compute"]'),
('portfolio.get_current_positions', '读取当前用户持仓列表', 'portfolio', 'java', true,
 '[]', '[]', '["READ_PORTFOLIO"]', '["portfolio_read"]'),
('portfolio.get_account_snapshot', '读取当前用户账户快照', 'portfolio', 'java', true,
 '[]', '[]', '["READ_PORTFOLIO"]', '["portfolio_read"]'),
('portfolio.get_transaction_history', '读取当前用户已发生成交流水', 'portfolio', 'java', true,
 '[]', '[]', '["READ_PORTFOLIO"]', '["portfolio_read"]'),
('portfolio.build_current_valuation', '基于最新行情做确定性估值重算', 'portfolio', 'local', true,
 '["positions_observation","account_observation","quote_observations"]',
 '["portfolio.get_current_positions","portfolio.get_account_snapshot"]',
 '["READ_PORTFOLIO"]', '["portfolio_read"]'),
('user.get_risk_profile', '读取当前用户风险画像与金融档案', 'user', 'java', true,
 '[]', '[]', '["READ_PROFILE"]', '["financial_profile_read"]');

INSERT INTO touchstone.tool_skills (skill_id, skill_version, domain, status, enabled) VALUES
('stock-research', '1.0.0', 'finance', 'CURRENT', true),
('portfolio-health', '1.0.0', 'finance', 'CURRENT', true),
('suitability-evaluation', '1.0.0', 'finance', 'FOUNDATION', false),
('forecast', '1.0.0', 'weather', 'EXPERIMENTAL', true);

INSERT INTO touchstone.tool_skill_operations (skill_id, code, required) VALUES
('stock-research', 'READ_MARKET_DATA', true),
('stock-research', 'RUN_ANALYSIS', true),
('stock-research', 'READ_PUBLIC_RESEARCH', false),
('portfolio-health', 'READ_PORTFOLIO', true),
('portfolio-health', 'READ_PROFILE', true),
('portfolio-health', 'READ_FINANCIAL_GOALS', false),
('portfolio-health', 'READ_MARKET_DATA', false),
('suitability-evaluation', 'READ_MARKET_DATA', true),
('suitability-evaluation', 'READ_PORTFOLIO', true),
('suitability-evaluation', 'READ_PROFILE', true),
('suitability-evaluation', 'RUN_ANALYSIS', true),
('suitability-evaluation', 'READ_PUBLIC_RESEARCH', false),
('forecast', 'READ_PUBLIC_RESEARCH', true);

INSERT INTO touchstone.tool_skill_capabilities (skill_id, capability, required) VALUES
('stock-research', 'market.resolve_instrument', true),
('stock-research', 'market.get_realtime_quote', true),
('stock-research', 'market.get_historical_prices', true),
('stock-research', 'market.get_financial_statements', true),
('stock-research', 'market.get_valuation', true),
('stock-research', 'market.get_industry_context', true),
('stock-research', 'market.get_money_flow', true),
('stock-research', 'market.get_news', true),
('stock-research', 'analysis.run_analysis', true),
('stock-research', 'research.web_search', false),
('stock-research', 'research.deep_search', false),
('portfolio-health', 'portfolio.get_current_positions', true),
('portfolio-health', 'portfolio.get_account_snapshot', true),
('portfolio-health', 'portfolio.build_current_valuation', true),
('portfolio-health', 'user.get_risk_profile', true),
('suitability-evaluation', 'market.resolve_instrument', true),
('suitability-evaluation', 'market.get_realtime_quote', true),
('suitability-evaluation', 'market.get_financial_statements', true),
('suitability-evaluation', 'market.get_valuation', true),
('suitability-evaluation', 'analysis.run_analysis', true),
('suitability-evaluation', 'portfolio.get_current_positions', true),
('suitability-evaluation', 'portfolio.get_account_snapshot', true),
('suitability-evaluation', 'portfolio.build_current_valuation', true),
('suitability-evaluation', 'user.get_risk_profile', true),
('suitability-evaluation', 'research.web_search', false),
('suitability-evaluation', 'research.deep_search', false);

CREATE INDEX idx_tool_capabilities_domain
    ON touchstone.tool_capabilities(domain, enabled);
CREATE INDEX idx_tool_capabilities_toolset
    ON touchstone.tool_capabilities(toolsets);

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('07-create-tool-catalog-tables.sql', '创建工具目录表并写入操作证、工具集、16 个工具能力和 4 个技能');

COMMIT;
