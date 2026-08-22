package com.bdlh.touchstone.data.repository;

import java.util.Map;
import java.util.UUID;

import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

/**
 * 每账号 LLM 接入配置（模型切换功能）。
 *
 * 安全约定：api_key 只存库；读取方（engine）仅在构建客户端时使用，
 * 任何接口响应/日志/工件不得携带明文（controller 层做脱敏投影）。
 */
@Repository
public class LlmConfigRepository {

    private final JdbcTemplate jdbc;

    public LlmConfigRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    /** 未配置时返回 null（controller 映射为 404），不抛异常。 */
    public Map<String, Object> find(UUID accountId) {
        try {
            return jdbc.queryForMap(
                    """
                    SELECT account_id, base_url, model, api_key, updated_at
                    FROM touchstone.account_llm_configs WHERE account_id = ?
                    """,
                    accountId);
        } catch (EmptyResultDataAccessException notFound) {
            return null;
        }
    }

    @Transactional
    public void upsert(UUID accountId, String baseUrl, String model, String apiKey) {
        jdbc.update(
                """
                INSERT INTO touchstone.account_llm_configs (account_id, base_url, model, api_key, updated_at)
                VALUES (?, ?, ?, ?, now())
                ON CONFLICT (account_id) DO UPDATE
                SET base_url = EXCLUDED.base_url,
                    model = EXCLUDED.model,
                    api_key = EXCLUDED.api_key,
                    updated_at = now()
                """,
                accountId, baseUrl, model, apiKey);
    }
}
