package com.bdlh.touchstone.data.api;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.bdlh.touchstone.data.repository.ToolFixtureRepository;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class ToolFixtureControllerTest {
    private ToolFixtureRepository repository;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        repository = Mockito.mock(ToolFixtureRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(new ToolFixtureController(repository)).build();
    }

    @Test
    void returnsFixtureSetWithResponses() throws Exception {
        when(repository.loadFixtureSet("ab-eval", 1))
                .thenReturn(Map.of(
                        "fixtureSetId", "ab-eval",
                        "fixtureSetVersion", 1,
                        "responses", List.of(Map.of(
                                "call_key", "market.get_realtime_quote",
                                "tool_name", "market.get_realtime_quote",
                                "arguments", Map.of(),
                                "response_status", "SUCCESS",
                                "response", Map.of("symbol", "300750", "price", 185.50),
                                "simulated_latency_ms", 5,
                                "sequence", 1))));

        mvc.perform(get("/internal/v1/tool-fixtures/ab-eval"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.fixtureSetId").value("ab-eval"))
                .andExpect(jsonPath("$.responses[0].call_key").value("market.get_realtime_quote"))
                .andExpect(jsonPath("$.responses[0].response.price").value(185.50));
    }

    @Test
    void returnsEmptyResponsesForUnknownSet() throws Exception {
        when(repository.loadFixtureSet("missing", 1))
                .thenReturn(Map.of(
                        "fixtureSetId", "missing",
                        "fixtureSetVersion", 1,
                        "responses", List.of()));

        mvc.perform(get("/internal/v1/tool-fixtures/missing"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.responses").isEmpty());
    }
}
