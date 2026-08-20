BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

-- 记录每次 Guardrail 检查的明细（四个时点：plan / action / data_quality / response）。
-- 拦截（block / modify / ask_user）必须记录，放行（allow）可按审计需求选择记录。
CREATE TABLE touchstone.guardrail_checks (
    id               UUID PRIMARY KEY,
    run_id           UUID NOT NULL
                     REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    sequence         INTEGER NOT NULL,
    stage            VARCHAR(30) NOT NULL,
    decision         VARCHAR(20) NOT NULL,
    audit_code       VARCHAR(100),
    rule_ids         JSONB NOT NULL DEFAULT '[]'::jsonb,
    reasons          JSONB NOT NULL DEFAULT '[]'::jsonb,
    tool_name        VARCHAR(200),
    tool_call_id     UUID REFERENCES touchstone.tool_calls(id),
    model_call_id    UUID REFERENCES touchstone.model_calls(id),
    subject_id       VARCHAR(200),
    detail           JSONB NOT NULL DEFAULT '{}'::jsonb,
    duration_ms      BIGINT NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, sequence),
    CONSTRAINT guardrail_stage_valid CHECK (
        stage IN ('plan', 'action', 'data_quality', 'response')
    ),
    CONSTRAINT guardrail_decision_valid CHECK (
        decision IN ('allow', 'block', 'modify', 'ask_user')
    ),
    CONSTRAINT guardrail_sequence_valid CHECK (sequence >= 0),
    CONSTRAINT guardrail_duration_valid CHECK (duration_ms >= 0),
    CONSTRAINT guardrail_decision_audit_valid CHECK (
        decision = 'allow' OR (audit_code IS NOT NULL AND audit_code <> '')
    )
);

-- 每次模型调用的输入消息快照，用于精确还原“第 N 次模型调用实际收到了什么”。
-- 首轮近似等于 context_messages，后续轮次在此基础上追加了工具结果。
-- 大消息正文通过 content_ref 引用对象存储，正文不进入数据库。
CREATE TABLE touchstone.model_call_messages (
    id               UUID PRIMARY KEY,
    run_id           UUID NOT NULL
                     REFERENCES touchstone.agent_runs(id) ON DELETE CASCADE,
    model_call_id    UUID NOT NULL,
    message_order    INTEGER NOT NULL,
    role             VARCHAR(30) NOT NULL,
    content          TEXT,
    content_ref      TEXT,
    tokens           INTEGER NOT NULL DEFAULT 0,
    content_hash     VARCHAR(100) NOT NULL,
    UNIQUE (model_call_id, message_order),
    FOREIGN KEY (model_call_id, run_id)
        REFERENCES touchstone.model_calls(id, run_id) ON DELETE CASCADE,
    CONSTRAINT model_call_message_role_valid CHECK (
        role IN ('system', 'user', 'assistant', 'tool')
    ),
    CONSTRAINT model_call_message_order_valid CHECK (message_order >= 0),
    CONSTRAINT model_call_message_tokens_valid CHECK (tokens >= 0),
    CONSTRAINT model_call_message_content_valid CHECK (
        content IS NOT NULL OR content_ref IS NOT NULL
    )
);

CREATE INDEX idx_guardrail_checks_run_stage
    ON touchstone.guardrail_checks(run_id, stage);
CREATE INDEX idx_guardrail_checks_tool_call
    ON touchstone.guardrail_checks(tool_call_id);
CREATE INDEX idx_guardrail_checks_model_call
    ON touchstone.guardrail_checks(model_call_id);
CREATE INDEX idx_model_call_messages_run
    ON touchstone.model_call_messages(run_id, model_call_id);

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('05-create-execution-detail-tables.sql', '创建守卫拦截明细和模型输入消息快照表');

COMMIT;
