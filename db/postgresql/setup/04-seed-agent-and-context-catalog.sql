BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

INSERT INTO touchstone.agent_implementations
    (id, name, implementation_type, description)
VALUES
    ('baseline-tool-calling', '直接 Tool Calling', 'DIRECT_TOOL_CALLING',
     '只保留模型原生工具调用循环，作为最小实现基线。'),
    ('langgraph-react', 'LangGraph ReAct', 'REACT_FRAMEWORK',
     '使用 LangGraph ReAct 执行循环，作为通用 Agent 框架实现。'),
    ('full-system', '完整工程实现', 'FULL_SYSTEM',
     '包含工具装载、权限校验、结果标准化、上下文处理和输出检查。');

INSERT INTO touchstone.agent_versions
    (agent_id, version, entrypoint, prompt_version, tool_catalog_version, runtime_config)
VALUES
    ('baseline-tool-calling', 'v1',
     'bdlh_runtime.evaluation.baseline_agent', 'system-base-v1', 'catalog-v1', '{}'),
    ('langgraph-react', 'v1',
     'bdlh_runtime.evaluation.baseline_langgraph', 'system-base-v1', 'catalog-v1', '{}'),
    ('full-system', 'v1',
     'bdlh_runtime.engine.runtime', 'system-base-v1', 'catalog-v1', '{}');

INSERT INTO touchstone.context_strategy_versions
    (strategy_id, version, name, strategy_type, algorithm_version, tokenizer_version, config)
VALUES
    ('full', 'v1', '完整上下文', 'FULL', 'context-builder-v1', 'runtime-selected', '{}'),
    ('recent-n', 'v1', '固定窗口', 'RECENT_N', 'context-builder-v1', 'runtime-selected',
     '{"recent_n":10}'),
    ('single-summary', 'v1', '一次性摘要', 'SINGLE_SUMMARY', 'context-builder-v1',
     'runtime-selected', '{"compression_ratio":0.35}'),
    ('budgeted', 'v1', '按预算选择和压缩', 'BUDGETED', 'context-builder-v1',
     'runtime-selected', '{"compression_ratio":0.35,"minimum_compressed_tokens":32}');

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('04-seed-agent-and-context-catalog.sql', '写入三种 Agent 实现和四种上下文策略');

COMMIT;
