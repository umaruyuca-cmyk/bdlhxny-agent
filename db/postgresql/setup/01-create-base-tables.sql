BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

CREATE SCHEMA IF NOT EXISTS touchstone;

CREATE TABLE touchstone.database_changes (
    script_name         VARCHAR(200) PRIMARY KEY,
    description         TEXT NOT NULL,
    applied_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    applied_by          VARCHAR(200) NOT NULL DEFAULT current_user
);

CREATE TABLE touchstone.case_definitions (
    id                  VARCHAR(100) PRIMARY KEY,
    title               VARCHAR(200) NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    current_version     INTEGER NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT case_status_valid CHECK (status IN ('ACTIVE', 'ARCHIVED'))
);

CREATE TABLE touchstone.case_versions (
    case_id             VARCHAR(100) NOT NULL REFERENCES touchstone.case_definitions(id),
    version             INTEGER NOT NULL,
    message             TEXT NOT NULL,
    scene               VARCHAR(50) NOT NULL,
    authenticated       BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_tools       JSONB NOT NULL DEFAULT '[]'::jsonb,
    context_profile     VARCHAR(100) NOT NULL DEFAULT 'default',
    token_budget        INTEGER NOT NULL,
    expected_checks     JSONB NOT NULL DEFAULT '{}'::jsonb,
    public              BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (case_id, version),
    CONSTRAINT case_token_budget_positive CHECK (token_budget > 0)
);

CREATE TABLE touchstone.case_variants (
    case_id             VARCHAR(100) NOT NULL,
    case_version        INTEGER NOT NULL,
    variant_id          VARCHAR(100) NOT NULL,
    title               VARCHAR(200) NOT NULL,
    context_strategy    VARCHAR(50) NOT NULL,
    token_budget        INTEGER NOT NULL,
    data_fixture        JSONB NOT NULL DEFAULT '{}'::jsonb,
    public              BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (case_id, case_version, variant_id),
    FOREIGN KEY (case_id, case_version)
        REFERENCES touchstone.case_versions(case_id, version)
);

CREATE TABLE touchstone.case_steps (
    case_id             VARCHAR(100) NOT NULL,
    case_version        INTEGER NOT NULL,
    step_number         INTEGER NOT NULL,
    message             TEXT NOT NULL,
    expected_checks     JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (case_id, case_version, step_number),
    FOREIGN KEY (case_id, case_version)
        REFERENCES touchstone.case_versions(case_id, version)
);

CREATE TABLE touchstone.data_snapshots (
    id                  VARCHAR(100) PRIMARY KEY,
    case_id             VARCHAR(100) NOT NULL,
    case_version        INTEGER NOT NULL,
    variant_id          VARCHAR(100) NOT NULL,
    fixture_version     VARCHAR(100) NOT NULL,
    market_as_of        TIMESTAMPTZ,
    content             JSONB NOT NULL,
    source_hash         VARCHAR(100) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, case_version, variant_id)
        REFERENCES touchstone.case_variants(case_id, case_version, variant_id)
);

CREATE TABLE touchstone.run_batches (
    id                  UUID PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    experiment_type     VARCHAR(50) NOT NULL,
    fixed_conditions    JSONB NOT NULL,
    status              VARCHAR(30) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ
);

CREATE TABLE touchstone.agent_runs (
    id                  UUID PRIMARY KEY,
    batch_id            UUID REFERENCES touchstone.run_batches(id),
    case_id             VARCHAR(100) NOT NULL,
    case_version        INTEGER NOT NULL,
    variant_id          VARCHAR(100) NOT NULL,
    snapshot_id         VARCHAR(100) NOT NULL REFERENCES touchstone.data_snapshots(id),
    agent_mode          VARCHAR(50) NOT NULL,
    context_strategy    VARCHAR(50) NOT NULL,
    model               VARCHAR(100) NOT NULL,
    model_config        JSONB NOT NULL DEFAULT '{}'::jsonb,
    git_commit          VARCHAR(64) NOT NULL,
    status              VARCHAR(30) NOT NULL,
    output              JSONB,
    error_category      VARCHAR(100),
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at        TIMESTAMPTZ,
    FOREIGN KEY (case_id, case_version, variant_id)
        REFERENCES touchstone.case_variants(case_id, case_version, variant_id)
);

CREATE TABLE touchstone.context_builds (
    id                          UUID PRIMARY KEY,
    run_id                      UUID NOT NULL REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    strategy                    VARCHAR(50) NOT NULL,
    tokenizer_version           VARCHAR(100) NOT NULL,
    compression_version         VARCHAR(100) NOT NULL,
    token_budget                INTEGER NOT NULL,
    original_tokens             INTEGER NOT NULL,
    working_tokens              INTEGER NOT NULL,
    compression_input_tokens    INTEGER NOT NULL DEFAULT 0,
    compression_output_tokens   INTEGER NOT NULL DEFAULT 0,
    duration_ms                 BIGINT NOT NULL,
    required_retained           BOOLEAN NOT NULL,
    budget_fit                  BOOLEAN NOT NULL,
    references_valid            BOOLEAN NOT NULL,
    instruction_isolated        BOOLEAN NOT NULL,
    status                      VARCHAR(30) NOT NULL,
    error_code                  VARCHAR(100),
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE touchstone.context_items (
    id                  UUID PRIMARY KEY,
    context_build_id    UUID NOT NULL REFERENCES touchstone.context_builds(id) ON DELETE CASCADE,
    item_key            VARCHAR(200) NOT NULL,
    item_type           VARCHAR(100) NOT NULL,
    classification      VARCHAR(30) NOT NULL,
    content             JSONB NOT NULL,
    content_ref         TEXT,
    source_id           VARCHAR(200),
    owner_id            VARCHAR(200),
    observed_at         TEXT,
    valid_from          TEXT,
    valid_to            TEXT,
    priority            INTEGER NOT NULL DEFAULT 0,
    trusted             BOOLEAN NOT NULL,
    raw_tokens          INTEGER NOT NULL,
    content_hash        VARCHAR(100) NOT NULL,
    sequence            INTEGER NOT NULL,
    UNIQUE (context_build_id, item_key),
    CONSTRAINT context_classification_valid
        CHECK (classification IN ('required', 'compressible', 'reference_only', 'distractor'))
);

CREATE TABLE touchstone.context_decisions (
    id                  UUID PRIMARY KEY,
    context_build_id    UUID NOT NULL REFERENCES touchstone.context_builds(id) ON DELETE CASCADE,
    item_key            VARCHAR(200) NOT NULL,
    action              VARCHAR(30) NOT NULL,
    reason              TEXT NOT NULL,
    input_tokens        INTEGER NOT NULL,
    output_tokens       INTEGER NOT NULL,
    output_content      JSONB,
    output_hash         VARCHAR(100),
    reference_id        VARCHAR(200),
    decision_order      INTEGER NOT NULL,
    UNIQUE (context_build_id, item_key),
    CONSTRAINT context_action_valid
        CHECK (action IN ('kept', 'compressed', 'referenced', 'omitted', 'isolated'))
);

CREATE TABLE touchstone.context_messages (
    id                  UUID PRIMARY KEY,
    context_build_id    UUID NOT NULL REFERENCES touchstone.context_builds(id) ON DELETE CASCADE,
    message_order       INTEGER NOT NULL,
    role                VARCHAR(30) NOT NULL,
    content             TEXT NOT NULL,
    content_hash        VARCHAR(100) NOT NULL,
    tokens              INTEGER NOT NULL,
    UNIQUE (context_build_id, message_order)
);

CREATE TABLE touchstone.run_events (
    id                  UUID PRIMARY KEY,
    run_id              UUID NOT NULL REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    sequence            INTEGER NOT NULL,
    event_type          VARCHAR(100) NOT NULL,
    payload             JSONB NOT NULL,
    occurred_at         TIMESTAMPTZ NOT NULL,
    UNIQUE (run_id, sequence)
);

CREATE TABLE touchstone.evaluation_results (
    id                  UUID PRIMARY KEY,
    run_id              UUID NOT NULL UNIQUE REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    evaluator_version   VARCHAR(100) NOT NULL,
    valid_run           BOOLEAN NOT NULL,
    status              VARCHAR(30) NOT NULL,
    checks              JSONB NOT NULL,
    metrics             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE touchstone.run_artifacts (
    id                  UUID PRIMARY KEY,
    run_id              UUID NOT NULL REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    artifact_type       VARCHAR(50) NOT NULL,
    storage_ref         TEXT NOT NULL,
    content_hash        VARCHAR(100) NOT NULL,
    public              BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, artifact_type)
);

CREATE INDEX idx_runs_batch ON touchstone.agent_runs(batch_id);
CREATE INDEX idx_runs_case ON touchstone.agent_runs(case_id, case_version, variant_id);
CREATE INDEX idx_context_builds_run ON touchstone.context_builds(run_id);
CREATE INDEX idx_context_items_source ON touchstone.context_items(source_id);
CREATE INDEX idx_run_events_run ON touchstone.run_events(run_id, sequence);

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('01-create-base-tables.sql', '创建 Touchstone 基础表、约束和索引');

COMMIT;
