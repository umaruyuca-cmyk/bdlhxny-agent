package com.bdlh.touchstone.data.api;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.bdlh.touchstone.data.domain.CaseView;
import com.bdlh.touchstone.data.repository.CaseRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class CaseControllerTest {
    private CaseRepository repository;
    private MockMvc mvc;
    private CaseView sample;

    @BeforeEach
    void setUp() throws Exception {
        repository = Mockito.mock(CaseRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(new CaseController(repository)).build();
        var json = new ObjectMapper();
        sample = new CaseView(
                "research-01",
                1,
                "固定行情查询",
                "宁德时代现在什么价",
                "market",
                false,
                json.readTree("[\"market.get_realtime_quote\"]"),
                "default",
                8192,
                json.readTree("{\"expected_tools\":[\"market.get_realtime_quote\"]}"),
                true);
    }

    @Test
    void listsOnlyRepositoryProvidedCases() throws Exception {
        when(repository.listCurrent()).thenReturn(List.of(sample));

        mvc.perform(get("/internal/v1/cases"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value("research-01"))
                .andExpect(jsonPath("$[0].message").value("宁德时代现在什么价"));
    }

    @Test
    void returnsNotFoundForUnknownVersion() throws Exception {
        when(repository.findVersion("missing", 1)).thenReturn(Optional.empty());

        mvc.perform(get("/internal/v1/cases/missing/versions/1"))
                .andExpect(status().isNotFound());
    }
}
