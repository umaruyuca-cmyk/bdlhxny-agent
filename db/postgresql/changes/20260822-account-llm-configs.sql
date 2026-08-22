-- 20260822-account-llm-configs.sql
-- 模型切换功能:每账号 LLM 接入配置表(提供商 base_url/模型/可选 API Key)。
--
-- 背景:页面需要按用户切换 LLM(类似模型下拉),API Key 选填并与账号绑定。
-- 安全取舍:Key 以明文存库(单机内部部署、无 KMS),但:
--   * 接口响应永不回明文(仅 hasApiKey/keyLast4);
--   * 不写日志、不进 fixed_conditions/model_config/运行工件/发布产物;
--   * PUT 时 apiKey 为 null/缺省=保留旧值,空串=清除,避免前端回显。
-- 幂等:CREATE TABLE IF NOT EXISTS,可安全重跑。
-- 服务影响:无需停服(data 服务按请求读库);engine 需重启加载新端点。
-- 回滚参考:DROP TABLE touchstone.account_llm_configs;

BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '1min';

CREATE TABLE IF NOT EXISTS touchstone.account_llm_configs (
    account_id   UUID PRIMARY KEY REFERENCES touchstone.accounts(id) ON DELETE CASCADE,
    base_url     TEXT NOT NULL,
    model        TEXT NOT NULL,
    api_key      TEXT,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO touchstone.database_changes (script_name, description)
VALUES ('20260822-account-llm-configs.sql', '模型切换:每账号 LLM 接入配置表(base_url/model/api_key,Key 只存库不出接口)')
ON CONFLICT DO NOTHING;

COMMIT;
