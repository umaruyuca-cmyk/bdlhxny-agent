package com.bdlh.touchstone.data.api;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.bdlh.touchstone.data.repository.PublicationRepository;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class PublicationControllerTest {
    private PublicationRepository repository;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        repository = Mockito.mock(PublicationRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(new PublicationController(repository)).build();
    }

    @Test
    void registersPublicationWithRunRows() throws Exception {
        String batchId = UUID.randomUUID().toString();
        String runId = UUID.randomUUID().toString();
        UUID publicationId = UUID.randomUUID();
        when(repository.registerPublication(Mockito.any())).thenReturn(publicationId);
        mvc.perform(post("/internal/v1/publications")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "batchId": "%s",
                                  "title": "正式批次发布",
                                  "status": "PUBLISHED",
                                  "fieldPolicyVersion": "showcase-v2",
                                  "indexStorageRef": "showcase-data/index.json",
                                  "contentHash": "sha256:index",
                                  "runs": [
                                    {"runId": "%s", "publicStorageRef": "showcase-data/runs/%s.json",
                                     "publicContentHash": "sha256:run"}
                                  ]
                                }
                                """.formatted(batchId, runId, runId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.publicationId").value(publicationId.toString()));

        var captor = org.mockito.ArgumentCaptor.forClass(
                com.bdlh.touchstone.data.domain.RunPayloads.RegisterPublicationRequest.class);
        verify(repository).registerPublication(captor.capture());
        org.junit.jupiter.api.Assertions.assertEquals(batchId, captor.getValue().batchId());
        org.junit.jupiter.api.Assertions.assertEquals(1, captor.getValue().runs().size());
    }

    @Test
    void rejectsPublicationWithoutRuns() throws Exception {
        String batchId = UUID.randomUUID().toString();
        mvc.perform(post("/internal/v1/publications")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"batchId":"%s","title":"t","status":"PUBLISHED",
                                 "fieldPolicyVersion":"v","indexStorageRef":"i",
                                 "contentHash":"h","runs":[]}
                                """.formatted(batchId)))
                .andExpect(status().isBadRequest());
    }

    @Test
    void listsAndGetsPublications() throws Exception {
        UUID publicationId = UUID.randomUUID();
        when(repository.listPublications(null)).thenReturn(List.of(Map.of("id", publicationId)));
        when(repository.getPublication(publicationId)).thenReturn(Map.of("id", publicationId, "runs", List.of()));

        mvc.perform(get("/internal/v1/publications"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].id").value(publicationId.toString()));

        mvc.perform(get("/internal/v1/publications/{id}", publicationId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.runs").isArray());
    }
}
