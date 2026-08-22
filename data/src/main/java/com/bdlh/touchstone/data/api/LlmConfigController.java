package com.bdlh.touchstone.data.api;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.bdlh.touchstone.data.domain.RunPayloads.LlmConfigRequest;
import com.bdlh.touchstone.data.repository.LlmConfigRepository;

import jakarta.validation.Valid;

/**
 * 每账号 LLM 接入配置（模型切换功能，内部端点）。
 *
 * 分层约定：GET 返回明文 apiKey——engine 构建客户端必需（本层已由
 * X-Internal-Token 保护）；对外脱敏（仅 hasApiKey/keyLast4）由 engine 层完成。
 * PUT 时 apiKey 为 null/缺省表示保留旧值、空串表示清除，响应为脱敏视图。
 */
@RestController
@RequestMapping("/internal/v1/llm-configs")
public class LlmConfigController {

    private final LlmConfigRepository configs;

    public LlmConfigController(LlmConfigRepository configs) {
        this.configs = configs;
    }

    @GetMapping("/{accountId}")
    public ResponseEntity<Map<String, Object>> get(@PathVariable UUID accountId) {
        Map<String, Object> row = configs.find(accountId);
        if (row == null) {
            return ResponseEntity.notFound().build();
        }
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("baseUrl", row.get("base_url"));
        view.put("model", row.get("model"));
        view.put("apiKey", row.get("api_key"));
        return ResponseEntity.ok(view);
    }

    @PutMapping("/{accountId}")
    public ResponseEntity<Map<String, Object>> save(
            @PathVariable UUID accountId,
            @Valid @RequestBody LlmConfigRequest request) {
        String apiKey = mergeApiKey(accountId, request.apiKey());
        configs.upsert(accountId, request.baseUrl(), request.model(), apiKey);
        Map<String, Object> row = configs.find(accountId);
        return ResponseEntity.ok(projection(row));
    }

    /** null/缺省=保留旧值；空串=清除；其余=覆盖。 */
    private String mergeApiKey(UUID accountId, String incoming) {
        if (incoming == null) {
            Map<String, Object> existing = configs.find(accountId);
            return existing == null ? null : (String) existing.get("api_key");
        }
        return incoming.isEmpty() ? null : incoming;
    }

    /** 脱敏投影：永不输出明文密钥。 */
    private Map<String, Object> projection(Map<String, Object> row) {
        String apiKey = (String) row.get("api_key");
        Map<String, Object> view = new LinkedHashMap<>();
        view.put("baseUrl", row.get("base_url"));
        view.put("model", row.get("model"));
        view.put("hasApiKey", apiKey != null && !apiKey.isEmpty());
        view.put("keyLast4", apiKey == null || apiKey.length() < 4 ? null : apiKey.substring(apiKey.length() - 4));
        return view;
    }
}
