package com.bdlh.touchstone.data.api;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.Map;
import java.util.UUID;

import com.bdlh.touchstone.data.repository.LlmConfigRepository;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class LlmConfigControllerTest {
    private LlmConfigRepository repository;
    private MockMvc mvc;
    private final UUID accountId = UUID.randomUUID();

    @BeforeEach
    void setUp() {
        repository = Mockito.mock(LlmConfigRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(new LlmConfigController(repository)).build();
    }

    @Test
    void getReturnsPlaintextKeyForEngine() throws Exception {
        // internal 层(令牌保护)返回明文,engine 构建客户端必需;对外脱敏在 engine 层
        when(repository.find(accountId)).thenReturn(Map.of(
                "account_id", accountId,
                "base_url", "https://open.bigmodel.cn/api/paas/v4",
                "model", "glm-4.7-flash",
                "api_key", "sk-secret-1234",
                "updated_at", java.time.Instant.now()));

        mvc.perform(get("/internal/v1/llm-configs/{id}", accountId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.baseUrl").value("https://open.bigmodel.cn/api/paas/v4"))
                .andExpect(jsonPath("$.model").value("glm-4.7-flash"))
                .andExpect(jsonPath("$.apiKey").value("sk-secret-1234"));
    }

    @Test
    void getReturns404WhenUnconfigured() throws Exception {
        when(repository.find(accountId)).thenReturn(null);
        mvc.perform(get("/internal/v1/llm-configs/{id}", accountId))
                .andExpect(status().isNotFound());
    }

    @Test
    void saveUpsertsAndMergesApiKey() throws Exception {
        // 已有旧 key;PUT 不带 apiKey 字段 → 保留旧值
        when(repository.find(accountId)).thenReturn(
                Map.of("account_id", accountId, "base_url", "https://old", "model", "old-model",
                        "api_key", "sk-keep-old", "updated_at", java.time.Instant.now()),
                Map.of("account_id", accountId, "base_url", "https://api.deepseek.com/v1",
                        "model", "deepseek-chat", "api_key", "sk-keep-old",
                        "updated_at", java.time.Instant.now()));

        mvc.perform(put("/internal/v1/llm-configs/{id}", accountId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"baseUrl\":\"https://api.deepseek.com/v1\",\"model\":\"deepseek-chat\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.model").value("deepseek-chat"))
                .andExpect(jsonPath("$.keyLast4").value("-old"));

        verify(repository).upsert(eq(accountId), eq("https://api.deepseek.com/v1"), eq("deepseek-chat"), eq("sk-keep-old"));
    }

    @Test
    void saveRejectsBlankFields() throws Exception {
        mvc.perform(put("/internal/v1/llm-configs/{id}", accountId)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"baseUrl\":\"\",\"model\":\"\"}"))
                .andExpect(status().isBadRequest());
        verify(repository, never()).upsert(any(), any(), any(), any());
    }
}
