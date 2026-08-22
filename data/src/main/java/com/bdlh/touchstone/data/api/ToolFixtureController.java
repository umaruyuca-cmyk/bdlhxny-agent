package com.bdlh.touchstone.data.api;

import com.bdlh.touchstone.data.repository.ToolFixtureRepository;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/v1/tool-fixtures")
public class ToolFixtureController {
    private final ToolFixtureRepository toolFixtures;

    public ToolFixtureController(ToolFixtureRepository toolFixtures) {
        this.toolFixtures = toolFixtures;
    }

    @GetMapping("/{fixtureSetId}")
    public ResponseEntity<Map<String, Object>> fixtureSet(
            @PathVariable String fixtureSetId, @RequestParam(defaultValue = "1") int version) {
        return ResponseEntity.ok(toolFixtures.loadFixtureSet(fixtureSetId, version));
    }
}
