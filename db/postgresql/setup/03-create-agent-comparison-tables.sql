BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

-- 让“固定输入 -> 上下文处理 -> Agent 执行 -> 评测 -> 发布”可以按版本追溯。
-- 基础表中的字符串字段继续保留，已有调用方可以逐步迁移到下面的版本表。

CREATE TABLE touchstone.agent_implementations (
    id                  VARCHAR(100) PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    implementation_type VARCHAR(40) NOT NULL,
    description         TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT agent_implementation_type_valid CHECK (
        implementation_type IN ('DIRECT_TOOL_CALLING', 'REACT_FRAMEWORK', 'FULL_SYSTEM')
    ),
    CONSTRAINT agent_implementation_status_valid CHECK (status IN ('ACTIVE', 'ARCHIVED'))
);

CREATE TABLE touchstone.agent_versions (
    agent_id             VARCHAR(100) NOT NULL
                         REFERENCES touchstone.agent_implementations(id),
    version              VARCHAR(100) NOT NULL,
    entrypoint           VARCHAR(300) NOT NULL,
    prompt_version       VARCHAR(100) NOT NULL,
    tool_catalog_version VARCHAR(100) NOT NULL,
    source_git_commit    VARCHAR(64),
    runtime_config       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (agent_id, version)
);

CREATE TABLE touchstone.context_strategy_versions (
    strategy_id          VARCHAR(100) NOT NULL,
    version              VARCHAR(100) NOT NULL,
    name                 VARCHAR(200) NOT NULL,
    strategy_type        VARCHAR(30) NOT NULL,
    algorithm_version    VARCHAR(100) NOT NULL,
    tokenizer_version    VARCHAR(100) NOT NULL,
    config               JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (strategy_id, version),
    CONSTRAINT context_strategy_type_valid CHECK (
        strategy_type IN ('FULL', 'RECENT_N', 'SINGLE_SUMMARY', 'BUDGETED')
    )
);

-- 固定数据集用于保存可重复运行的长上下文和工具返回。
-- 运行开始时仍要生成 data_snapshots，避免后来修改数据集影响历史运行。
CREATE TABLE touchstone.fixture_sets (
    id                  VARCHAR(100) NOT NULL,
    version             INTEGER NOT NULL,
    title               VARCHAR(200) NOT NULL,
    fixture_type        VARCHAR(20) NOT NULL,
    source_hash         VARCHAR(100) NOT NULL,
    captured_at         TIMESTAMPTZ,
    public              BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, version),
    CONSTRAINT fixture_version_positive CHECK (version > 0),
    CONSTRAINT fixture_type_valid CHECK (fixture_type IN ('STATIC', 'RECORDED'))
);

CREATE TABLE touchstone.case_variant_fixtures (
    case_id             VARCHAR(100) NOT NULL,
    case_version        INTEGER NOT NULL,
    variant_id          VARCHAR(100) NOT NULL,
    purpose             VARCHAR(30) NOT NULL,
    fixture_set_id      VARCHAR(100) NOT NULL,
    fixture_set_version INTEGER NOT NULL,
    PRIMARY KEY (case_id, case_version, variant_id, purpose),
    FOREIGN KEY (case_id, case_version, variant_id)
        REFERENCES touchstone.case_variants(case_id, case_version, variant_id),
    FOREIGN KEY (fixture_set_id, fixture_set_version)
        REFERENCES touchstone.fixture_sets(id, version),
    CONSTRAINT fixture_purpose_valid CHECK (
        purpose IN ('CONTEXT', 'TOOLS', 'PROFILE', 'MARKET')
    )
);

CREATE TABLE touchstone.fixture_context_items (
    fixture_set_id      VARCHAR(100) NOT NULL,
    fixture_set_version INTEGER NOT NULL,
    item_key            VARCHAR(200) NOT NULL,
    item_type           VARCHAR(100) NOT NULL,
    classification      VARCHAR(30) NOT NULL,
    content             JSONB NOT NULL DEFAULT '{}'::jsonb,
    content_ref         TEXT,
    source_ref          TEXT NOT NULL,
    observed_at         TIMESTAMPTZ,
    priority            INTEGER NOT NULL DEFAULT 0,
    trusted             BOOLEAN NOT NULL,
    raw_tokens          INTEGER,
    content_hash        VARCHAR(100) NOT NULL,
    sequence            INTEGER NOT NULL,
    PRIMARY KEY (fixture_set_id, fixture_set_version, item_key),
    FOREIGN KEY (fixture_set_id, fixture_set_version)
        REFERENCES touchstone.fixture_sets(id, version) ON DELETE CASCADE,
    CONSTRAINT fixture_context_classification_valid CHECK (
        classification IN ('required', 'compressible', 'reference_only', 'distractor')
    ),
    CONSTRAINT fixture_context_tokens_valid CHECK (raw_tokens IS NULL OR raw_tokens >= 0),
    CONSTRAINT fixture_context_sequence_valid CHECK (sequence >= 0)
);

CREATE TABLE touchstone.fixture_tool_responses (
    fixture_set_id      VARCHAR(100) NOT NULL,
    fixture_set_version INTEGER NOT NULL,
    call_key            VARCHAR(200) NOT NULL,
    tool_name           VARCHAR(200) NOT NULL,
    arguments           JSONB NOT NULL,
    arguments_hash      VARCHAR(100) NOT NULL,
    response_status     VARCHAR(30) NOT NULL,
    response            JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_ref        TEXT,
    response_hash       VARCHAR(100) NOT NULL,
    observed_at         TIMESTAMPTZ,
    simulated_latency_ms BIGINT NOT NULL DEFAULT 0,
    sequence            INTEGER NOT NULL,
    PRIMARY KEY (fixture_set_id, fixture_set_version, call_key),
    FOREIGN KEY (fixture_set_id, fixture_set_version)
        REFERENCES touchstone.fixture_sets(id, version) ON DELETE CASCADE,
    CONSTRAINT fixture_tool_status_valid CHECK (
        response_status IN ('SUCCESS', 'TIMEOUT', 'ERROR', 'DENIED')
    ),
    CONSTRAINT fixture_tool_latency_valid CHECK (simulated_latency_ms >= 0),
    CONSTRAINT fixture_tool_sequence_valid CHECK (sequence >= 0)
);

ALTER TABLE touchstone.data_snapshots
    ADD COLUMN fixture_set_id VARCHAR(100),
    ADD COLUMN fixture_set_version INTEGER,
    ADD CONSTRAINT data_snapshot_fixture_fk
        FOREIGN KEY (fixture_set_id, fixture_set_version)
        REFERENCES touchstone.fixture_sets(id, version),
    ADD CONSTRAINT data_snapshot_fixture_pair_valid CHECK (
        (fixture_set_id IS NULL AND fixture_set_version IS NULL)
        OR (fixture_set_id IS NOT NULL AND fixture_set_version IS NOT NULL)
    );

ALTER TABLE touchstone.run_batches
    ADD COLUMN experiment_variable VARCHAR(30),
    ADD COLUMN requested_repetitions INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN random_seed BIGINT,
    ADD COLUMN created_by VARCHAR(200),
    ADD COLUMN idempotency_key VARCHAR(200),
    ADD COLUMN started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD CONSTRAINT run_batch_experiment_variable_valid CHECK (
        experiment_variable IS NULL
        OR experiment_variable IN ('AGENT_IMPLEMENTATION', 'CONTEXT_STRATEGY')
    ),
    ADD CONSTRAINT run_batch_repetitions_positive CHECK (requested_repetitions > 0),
    ADD CONSTRAINT run_batch_idempotency_unique UNIQUE (idempotency_key);

ALTER TABLE touchstone.agent_runs
    ADD COLUMN agent_id VARCHAR(100),
    ADD COLUMN agent_version VARCHAR(100),
    ADD COLUMN context_strategy_id VARCHAR(100),
    ADD COLUMN context_strategy_version VARCHAR(100),
    ADD COLUMN repeat_index INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN random_seed BIGINT,
    ADD COLUMN idempotency_key VARCHAR(200),
    ADD COLUMN started_at TIMESTAMPTZ,
    ADD CONSTRAINT agent_run_agent_version_fk
        FOREIGN KEY (agent_id, agent_version)
        REFERENCES touchstone.agent_versions(agent_id, version),
    ADD CONSTRAINT agent_run_context_strategy_fk
        FOREIGN KEY (context_strategy_id, context_strategy_version)
        REFERENCES touchstone.context_strategy_versions(strategy_id, version),
    ADD CONSTRAINT agent_run_agent_pair_valid CHECK (
        (agent_id IS NULL AND agent_version IS NULL)
        OR (agent_id IS NOT NULL AND agent_version IS NOT NULL)
    ),
    ADD CONSTRAINT agent_run_context_strategy_pair_valid CHECK (
        (context_strategy_id IS NULL AND context_strategy_version IS NULL)
        OR (context_strategy_id IS NOT NULL AND context_strategy_version IS NOT NULL)
    ),
    ADD CONSTRAINT agent_run_repeat_index_valid CHECK (repeat_index >= 0),
    ADD CONSTRAINT agent_run_idempotency_unique UNIQUE (idempotency_key);

-- 基础表为兼容早期接口使用了文本时间。新接口写入带类型的时间列，旧列待数据迁移后删除。
ALTER TABLE touchstone.context_items
    ADD COLUMN observed_at_time TIMESTAMPTZ,
    ADD COLUMN valid_from_time TIMESTAMPTZ,
    ADD COLUMN valid_to_time TIMESTAMPTZ;

-- 一次模型请求一行，包括主 Agent、上下文压缩和评测模型调用。
CREATE TABLE touchstone.model_calls (
    id                  UUID PRIMARY KEY,
    run_id              UUID NOT NULL REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    sequence            INTEGER NOT NULL,
    purpose             VARCHAR(30) NOT NULL,
    model               VARCHAR(100) NOT NULL,
    request_hash        VARCHAR(100) NOT NULL,
    response_hash       VARCHAR(100),
    input_tokens        INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens       INTEGER NOT NULL DEFAULT 0,
    duration_ms         BIGINT NOT NULL DEFAULT 0,
    retry_count         INTEGER NOT NULL DEFAULT 0,
    status              VARCHAR(30) NOT NULL,
    error_category      VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, sequence),
    UNIQUE (id, run_id),
    CONSTRAINT model_call_purpose_valid CHECK (purpose IN ('AGENT', 'COMPRESSION', 'JUDGMENT')),
    CONSTRAINT model_call_status_valid CHECK (status IN ('COMPLETE', 'FAILED', 'INVALID')),
    CONSTRAINT model_call_numbers_valid CHECK (
        sequence >= 0 AND input_tokens >= 0 AND cached_input_tokens >= 0
        AND output_tokens >= 0 AND duration_ms >= 0 AND retry_count >= 0
    )
);

-- 工具调用单独存储，网页可以直接展示工具选择、参数、来源和耗时。
CREATE TABLE touchstone.tool_calls (
    id                  UUID PRIMARY KEY,
    run_id              UUID NOT NULL REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    model_call_id       UUID,
    sequence            INTEGER NOT NULL,
    tool_name           VARCHAR(200) NOT NULL,
    arguments           JSONB NOT NULL,
    arguments_hash      VARCHAR(100) NOT NULL,
    status              VARCHAR(30) NOT NULL,
    result_summary      JSONB NOT NULL DEFAULT '{}'::jsonb,
    result_ref          TEXT,
    result_hash         VARCHAR(100),
    source_time         TIMESTAMPTZ,
    duration_ms         BIGINT NOT NULL DEFAULT 0,
    audit_code          VARCHAR(100),
    fixture_hit         BOOLEAN NOT NULL DEFAULT FALSE,
    error_category      VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, sequence),
    FOREIGN KEY (model_call_id, run_id)
        REFERENCES touchstone.model_calls(id, run_id),
    CONSTRAINT tool_call_status_valid CHECK (
        status IN ('SUCCESS', 'FAILED', 'TIMEOUT', 'DENIED', 'INVALID')
    ),
    CONSTRAINT tool_call_numbers_valid CHECK (sequence >= 0 AND duration_ms >= 0)
);

-- 网页常用的 token、成本和分阶段耗时放在固定列中，便于 SQL 聚合 p50/p95。
CREATE TABLE touchstone.run_measurements (
    run_id                      UUID PRIMARY KEY
                                REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    queue_ms                    BIGINT NOT NULL DEFAULT 0,
    snapshot_ms                 BIGINT NOT NULL DEFAULT 0,
    context_collect_ms          BIGINT NOT NULL DEFAULT 0,
    context_compress_ms         BIGINT NOT NULL DEFAULT 0,
    tool_loading_ms             BIGINT NOT NULL DEFAULT 0,
    llm_ms                      BIGINT NOT NULL DEFAULT 0,
    tool_ms                     BIGINT NOT NULL DEFAULT 0,
    guardrail_ms                BIGINT NOT NULL DEFAULT 0,
    judgment_ms                 BIGINT NOT NULL DEFAULT 0,
    first_output_ms             BIGINT,
    total_duration_ms           BIGINT NOT NULL,
    prompt_tokens               INTEGER NOT NULL DEFAULT 0,
    cached_prompt_tokens        INTEGER NOT NULL DEFAULT 0,
    completion_tokens           INTEGER NOT NULL DEFAULT 0,
    compression_input_tokens    INTEGER NOT NULL DEFAULT 0,
    compression_output_tokens   INTEGER NOT NULL DEFAULT 0,
    estimated_model_cost        NUMERIC(18, 8),
    estimated_compression_cost  NUMERIC(18, 8),
    currency                    VARCHAR(10),
    pricing_snapshot            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT run_measurement_numbers_valid CHECK (
        queue_ms >= 0 AND snapshot_ms >= 0 AND context_collect_ms >= 0
        AND context_compress_ms >= 0 AND tool_loading_ms >= 0 AND llm_ms >= 0
        AND tool_ms >= 0 AND guardrail_ms >= 0 AND judgment_ms >= 0
        AND (first_output_ms IS NULL OR first_output_ms >= 0) AND total_duration_ms >= 0
        AND prompt_tokens >= 0 AND cached_prompt_tokens >= 0 AND completion_tokens >= 0
        AND compression_input_tokens >= 0 AND compression_output_tokens >= 0
        AND (estimated_model_cost IS NULL OR estimated_model_cost >= 0)
        AND (estimated_compression_cost IS NULL OR estimated_compression_cost >= 0)
    )
);

-- 高频聚合指标单独成行，完整评测说明仍保留在 evaluation_results.checks/metrics。
CREATE TABLE touchstone.evaluation_metrics (
    run_id              UUID NOT NULL
                        REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    metric_name         VARCHAR(100) NOT NULL,
    metric_value        NUMERIC(20, 8),
    passed              BOOLEAN,
    unit                VARCHAR(30),
    details             JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (run_id, metric_name),
    CONSTRAINT evaluation_metric_has_value CHECK (
        metric_value IS NOT NULL OR passed IS NOT NULL
    )
);

-- 发布记录只保存内部批次与静态公开工件之间的映射。
-- 公共网页仍然不连接 PostgreSQL。
CREATE TABLE touchstone.publications (
    id                   UUID PRIMARY KEY,
    batch_id             UUID NOT NULL REFERENCES touchstone.run_batches(id),
    version              INTEGER NOT NULL,
    title                VARCHAR(200) NOT NULL,
    status               VARCHAR(30) NOT NULL,
    field_policy_version VARCHAR(100) NOT NULL,
    index_storage_ref    TEXT,
    content_hash         VARCHAR(100),
    generated_at         TIMESTAMPTZ,
    published_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (batch_id, version),
    CONSTRAINT publication_version_positive CHECK (version > 0),
    CONSTRAINT publication_status_valid CHECK (
        status IN ('DRAFT', 'VALIDATED', 'PUBLISHED', 'REJECTED')
    )
);

CREATE TABLE touchstone.publication_runs (
    publication_id      UUID NOT NULL
                        REFERENCES touchstone.publications(id) ON DELETE CASCADE,
    run_id              UUID NOT NULL REFERENCES touchstone.agent_runs(id),
    public_storage_ref  TEXT NOT NULL,
    public_content_hash VARCHAR(100) NOT NULL,
    PRIMARY KEY (publication_id, run_id)
);

CREATE INDEX idx_agent_runs_comparison
    ON touchstone.agent_runs(batch_id, case_id, case_version, variant_id, repeat_index);
CREATE INDEX idx_agent_runs_version
    ON touchstone.agent_runs(agent_id, agent_version);
CREATE INDEX idx_agent_runs_strategy_version
    ON touchstone.agent_runs(context_strategy_id, context_strategy_version);
CREATE INDEX idx_model_calls_run_purpose
    ON touchstone.model_calls(run_id, purpose, sequence);
CREATE INDEX idx_tool_calls_run_tool
    ON touchstone.tool_calls(run_id, tool_name, sequence);
CREATE INDEX idx_fixture_context_sequence
    ON touchstone.fixture_context_items(fixture_set_id, fixture_set_version, sequence);
CREATE INDEX idx_fixture_tool_name
    ON touchstone.fixture_tool_responses(fixture_set_id, fixture_set_version, tool_name);
CREATE INDEX idx_evaluation_metrics_name
    ON touchstone.evaluation_metrics(metric_name, metric_value);
CREATE INDEX idx_publications_status
    ON touchstone.publications(status, published_at DESC);

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('03-create-agent-comparison-tables.sql', '创建 Agent 对照、调用明细、指标和发布记录表');

COMMIT;
