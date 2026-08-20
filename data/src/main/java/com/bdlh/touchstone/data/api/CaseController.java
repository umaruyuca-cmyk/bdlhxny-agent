package com.bdlh.touchstone.data.api;

import com.bdlh.touchstone.data.domain.CaseView;
import com.bdlh.touchstone.data.repository.CaseRepository;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/v1/cases")
public class CaseController {
    private final CaseRepository cases;

    public CaseController(CaseRepository cases) {
        this.cases = cases;
    }

    @GetMapping
    public List<CaseView> listCurrent() {
        return cases.listCurrent();
    }

    @GetMapping("/{caseId}/current")
    public ResponseEntity<CaseView> current(@PathVariable String caseId) {
        return cases.findCurrent(caseId)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    @GetMapping("/{caseId}/versions/{version}")
    public ResponseEntity<CaseView> version(
            @PathVariable String caseId, @PathVariable int version) {
        return cases.findVersion(caseId, version)
                .map(ResponseEntity::ok)
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
