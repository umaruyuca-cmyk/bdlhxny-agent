package com.bdlh.touchstone.data.repository;

import com.bdlh.touchstone.data.domain.CaseView;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.bdlh.touchstone.data.domain.VariantContextView;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class CaseRepository {
    private static final String SELECT_COLUMNS = """
            SELECT d.id, v.version, d.title, v.message, v.scene, v.authenticated,
                   v.allowed_tools, v.context_profile, v.token_budget,
                   v.expected_checks, v.public,
                   COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                                  'stepNumber', s.step_number,
                                  'message', s.message,
                                  'assistant', (s.expected_checks ->> 'role') = 'assistant_fixture'
                              ) ORDER BY s.step_number)
                       FROM touchstone.case_steps s
                       WHERE s.case_id = d.id AND s.case_version = v.version
                   ), '[]'::jsonb) AS steps,
                   COALESCE((
                       SELECT jsonb_agg(jsonb_build_object(
                                  'variantId', cv.variant_id,
                                  'contextStrategy', cv.context_strategy,
                                  'tokenBudget', cv.token_budget,
                                  'snapshotId', ds.id,
                                  'snapshotHash', ds.source_hash
                              ) ORDER BY cv.variant_id)
                       FROM touchstone.case_variants cv
                       LEFT JOIN touchstone.data_snapshots ds
                         ON ds.case_id = cv.case_id
                        AND ds.case_version = cv.case_version
                        AND ds.variant_id = cv.variant_id
                       WHERE cv.case_id = d.id AND cv.case_version = v.version
                   ), '[]'::jsonb) AS variants
            FROM touchstone.case_definitions d
            JOIN touchstone.case_versions v
              ON v.case_id = d.id
            """;

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public CaseRepository(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    public List<CaseView> listCurrent() {
        return jdbc.query(
                SELECT_COLUMNS
                        + " WHERE v.version = d.current_version AND d.status = 'ACTIVE' ORDER BY d.id",
                this::map);
    }

    public Optional<CaseView> findVersion(String caseId, int version) {
        List<CaseView> rows = jdbc.query(
                SELECT_COLUMNS + " WHERE d.id = ? AND v.version = ?",
                this::map,
                caseId,
                version);
        return rows.stream().findFirst();
    }

    public Optional<CaseView> findCurrent(String caseId) {
        List<CaseView> rows = jdbc.query(
                SELECT_COLUMNS + " WHERE d.id = ? AND v.version = d.current_version",
                this::map,
                caseId);
        return rows.stream().findFirst();
    }

    /** 变体上下文条目:优先 fixture_context_items 正规表,兼容 data_fixture JSONB。 */
    public Optional<VariantContextView> findVariantContext(String caseId, int version, String variantId) {
        List<VariantContextView.VariantContextItem> fixtureItems = jdbc.query(
                """
                SELECT fci.item_key, fci.item_type, fci.classification,
                       fci.content::text AS content, fci.source_ref, fci.observed_at,
                       fci.priority, fci.trusted, fci.sequence
                FROM touchstone.case_variant_fixtures cvf
                JOIN touchstone.fixture_context_items fci
                  ON fci.fixture_set_id = cvf.fixture_set_id
                 AND fci.fixture_set_version = cvf.fixture_set_version
                WHERE cvf.case_id = ? AND cvf.case_version = ? AND cvf.variant_id = ?
                  AND cvf.purpose = 'CONTEXT'
                ORDER BY fci.sequence
                """,
                (rs, rowNumber) -> new VariantContextView.VariantContextItem(
                        rs.getString("item_key"),
                        rs.getString("item_type"),
                        rs.getString("classification"),
                        readContent(rs.getString("content")),
                        rs.getInt("priority"),
                        rs.getBoolean("trusted"),
                        rs.getInt("sequence"),
                        !rs.getBoolean("trusted"),
                        false,
                        null,
                        null,
                        false,
                        null,
                        rs.getString("observed_at")),
                caseId,
                version,
                variantId);
        VariantMeta meta = findVariantMeta(caseId, version, variantId);
        if (meta == null) {
            return Optional.empty();
        }
        if (!fixtureItems.isEmpty()) {
            return Optional.of(new VariantContextView(
                    caseId, version, variantId, meta.strategy(), meta.budget(),
                    "fixture_context_items", fixtureItems));
        }
        return Optional.of(new VariantContextView(
                caseId, version, variantId, meta.strategy(), meta.budget(),
                "data_fixture", fixtureItemsFromFixtureJson(meta.fixtureJson())));
    }

    private record VariantMeta(String strategy, int budget, JsonNode fixtureJson) {}

    private VariantMeta findVariantMeta(String caseId, int version, String variantId) {
        List<VariantMeta> rows = jdbc.query(
                """
                SELECT context_strategy, token_budget, data_fixture
                FROM touchstone.case_variants
                WHERE case_id = ? AND case_version = ? AND variant_id = ?
                """,
                (rs, rowNumber) -> new VariantMeta(
                        rs.getString("context_strategy"),
                        rs.getInt("token_budget"),
                        readTreeQuietly(rs.getString("data_fixture"))),
                caseId,
                version,
                variantId);
        return rows.stream().findFirst().orElse(null);
    }

    private List<VariantContextView.VariantContextItem> fixtureItemsFromFixtureJson(JsonNode fixture) {
        List<VariantContextView.VariantContextItem> items = new ArrayList<>();
        if (fixture == null || !fixture.has("context_items")) {
            return items;
        }
        int index = 0;
        for (JsonNode node : fixture.get("context_items")) {
            String classification = node.has("classification")
                    ? node.get("classification").asText()
                    : (node.path("required").asBoolean(false) ? "required" : "compressible");
            boolean untrusted = node.path("untrusted").asBoolean(false);
            items.add(new VariantContextView.VariantContextItem(
                    node.path("item_key").asText(""),
                    node.path("item_type").asText("generic"),
                    classification,
                    node.path("content").isTextual()
                            ? node.path("content").asText()
                            : node.path("content").toString(),
                    node.path("priority").asInt(0),
                    !untrusted,
                    index,
                    untrusted,
                    node.path("stale").asBoolean(false),
                    textOrNull(node, "valid_from"),
                    textOrNull(node, "valid_to"),
                    node.path("cross_user").asBoolean(false),
                    textOrNull(node, "duplicate_of"),
                    null));
            index += 1;
        }
        return items;
    }

    private String readContent(String raw) {
        try {
            JsonNode node = objectMapper.readTree(raw);
            return node.isTextual() ? node.asText() : node.toString();
        } catch (JsonProcessingException exception) {
            return raw;
        }
    }

    private String textOrNull(JsonNode node, String field) {
        JsonNode value = node.get(field);
        return value == null || value.isNull() ? null : value.asText();
    }

    private JsonNode readTreeQuietly(String raw) {
        try {
            return objectMapper.readTree(raw);
        } catch (JsonProcessingException exception) {
            return null;
        }
    }

    private CaseView map(ResultSet rs, int rowNumber) throws SQLException {
        return new CaseView(
                rs.getString("id"),
                rs.getInt("version"),
                rs.getString("title"),
                rs.getString("message"),
                rs.getString("scene"),
                rs.getBoolean("authenticated"),
                readJson(rs.getString("allowed_tools")),
                rs.getString("context_profile"),
                rs.getInt("token_budget"),
                readJson(rs.getString("expected_checks")),
                rs.getBoolean("public"),
                readJson(rs.getString("steps")),
                readJson(rs.getString("variants")));
    }

    private JsonNode readJson(String value) throws SQLException {
        try {
            return objectMapper.readTree(value);
        } catch (JsonProcessingException exception) {
            throw new SQLException("invalid JSON stored in case catalog", exception);
        }
    }
}
