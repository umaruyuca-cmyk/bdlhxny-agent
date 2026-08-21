package com.bdlh.touchstone.data.repository;

import com.bdlh.touchstone.data.domain.CaseView;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.ResultSet;
import java.sql.SQLException;
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
