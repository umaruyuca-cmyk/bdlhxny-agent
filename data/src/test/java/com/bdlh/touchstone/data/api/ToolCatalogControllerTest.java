package com.bdlh.touchstone.data.api;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.bdlh.touchstone.data.repository.ToolCatalogRepository;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class ToolCatalogControllerTest {
    private ToolCatalogRepository repository;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        repository = Mockito.mock(ToolCatalogRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(new ToolCatalogController(repository)).build();
    }

    @Test
    void returnsFullCatalog() throws Exception {
        when(repository.loadCatalog()).thenReturn(Map.of(
                "operations", List.of(Map.of("code", "READ_MARKET_DATA", "description", "读取公开市场数据")),
                "toolsets", List.of(Map.of("name", "market_read", "description", "行情读取")),
                "capabilities", List.of(Map.of(
                        "name", "market.get_realtime_quote",
                        "adapter", "mcp",
                        "requires_authenticated_user", false,
                        "required_arguments", List.of("symbol"),
                        "operations", List.of("READ_MARKET_DATA"),
                        "toolsets", List.of("market_read"))),
                "skills", List.of(Map.of(
                        "skill_id", "stock-research",
                        "status", "CURRENT",
                        "enabled", true,
                        "operations", List.of(Map.of("code", "READ_MARKET_DATA", "required", true)),
                        "capabilities", List.of()))));

        mvc.perform(get("/internal/v1/tool-catalog"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.operations[0].code").value("READ_MARKET_DATA"))
                .andExpect(jsonPath("$.capabilities[0].name").value("market.get_realtime_quote"))
                .andExpect(jsonPath("$.capabilities[0].required_arguments[0]").value("symbol"))
                .andExpect(jsonPath("$.skills[0].skill_id").value("stock-research"))
                .andExpect(jsonPath("$.skills[0].operations[0].code").value("READ_MARKET_DATA"));
    }
}
