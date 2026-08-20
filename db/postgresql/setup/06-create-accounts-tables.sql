BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '5min';

-- 所有者账号。password_hash 保存 bcrypt/argon2 加盐 hash，绝不保存明文密码。
-- 账号由部署流程创建（见 setup/README.md），本脚本不写入任何账号或密码。
CREATE TABLE touchstone.accounts (
    id               UUID PRIMARY KEY,
    username         VARCHAR(100) NOT NULL,
    display_name     VARCHAR(200) NOT NULL,
    password_hash    VARCHAR(300) NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    failed_attempts  INTEGER NOT NULL DEFAULT 0,
    locked_until     TIMESTAMPTZ,
    last_login_at    TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT account_username_unique UNIQUE (username),
    CONSTRAINT account_status_valid CHECK (status IN ('ACTIVE', 'LOCKED', 'DISABLED')),
    CONSTRAINT account_failed_attempts_valid CHECK (failed_attempts >= 0)
);

-- 登录会话。token_hash 保存登录令牌的 sha256:<hex>，不保存明文令牌。
CREATE TABLE touchstone.auth_sessions (
    id               UUID PRIMARY KEY,
    account_id       UUID NOT NULL
                     REFERENCES touchstone.accounts(id) ON DELETE CASCADE,
    token_hash       VARCHAR(100) NOT NULL,
    expires_at       TIMESTAMPTZ NOT NULL,
    last_seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at       TIMESTAMPTZ,
    user_agent       TEXT,
    ip_address       VARCHAR(100),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT auth_session_token_hash_unique UNIQUE (token_hash),
    CONSTRAINT auth_session_expiry_valid CHECK (expires_at > created_at)
);

-- 登录和关键操作审计（登录成败、运行创建、发布等）。
CREATE TABLE touchstone.audit_log (
    id               UUID PRIMARY KEY,
    account_id       UUID REFERENCES touchstone.accounts(id),
    action           VARCHAR(50) NOT NULL,
    succeeded        BOOLEAN NOT NULL,
    detail           JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address       VARCHAR(100),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_auth_sessions_account
    ON touchstone.auth_sessions(account_id);
CREATE INDEX idx_audit_log_account_time
    ON touchstone.audit_log(account_id, created_at);
CREATE INDEX idx_audit_log_action_time
    ON touchstone.audit_log(action, created_at);

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('06-create-accounts-tables.sql', '创建所有者账号、登录会话和审计表');

COMMIT;
