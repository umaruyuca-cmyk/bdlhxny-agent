package com.bdlh.touchstone.data.api;

import com.bdlh.touchstone.data.repository.ToolCatalogRepository;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/internal/v1/tool-catalog")
public class ToolCatalogController {
    private final ToolCatalogRepository toolCatalog;

    public ToolCatalogController(ToolCatalogRepository toolCatalog) {
        this.toolCatalog = toolCatalog;
    }

    @GetMapping
    public Map<String, Object> catalog() {
        return toolCatalog.loadCatalog();
    }
}
