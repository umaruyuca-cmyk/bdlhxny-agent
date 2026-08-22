package com.bdlh.touchstone.data.api;

import static com.bdlh.touchstone.data.domain.RunPayloads.*;

import com.bdlh.touchstone.data.repository.PublicationRepository;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/v1/publications")
public class PublicationController {
    private final PublicationRepository publications;

    public PublicationController(PublicationRepository publications) {
        this.publications = publications;
    }

    /** 发布登记(任务五):发布产物 hash 与批次/运行的映射入库;version 自增。 */
    @PostMapping
    public Map<String, UUID> register(@Valid @RequestBody RegisterPublicationRequest request) {
        return Map.of("publicationId", publications.registerPublication(request));
    }

    @GetMapping
    public List<Map<String, Object>> list(@RequestParam(name = "batchId", required = false) String batchId) {
        return publications.listPublications(batchId);
    }

    @GetMapping("/{publicationId}")
    public ResponseEntity<Map<String, Object>> get(@PathVariable UUID publicationId) {
        try {
            return ResponseEntity.ok(publications.getPublication(publicationId));
        } catch (org.springframework.dao.EmptyResultDataAccessException exception) {
            return ResponseEntity.notFound().build();
        }
    }
}
