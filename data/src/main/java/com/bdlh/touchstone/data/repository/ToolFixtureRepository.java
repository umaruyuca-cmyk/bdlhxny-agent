package com.bdlh.touchstone.data.repository;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class ToolFixtureRepository {
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public ToolFixtureRepository(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> loadFixtureSet(String fixtureSetId, int version) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("fixtureSetId", fixtureSetId);
        result.put("fixtureSetVersion", version);
        result.put("responses", jdbc.query(
                """
                SELECT call_key, tool_name, arguments::text AS arguments, response_status,
                       response::text AS response, observed_at, simulated_latency_ms, sequence
                FROM touchstone.fixture_tool_responses
                WHERE fixture_set_id = ? AND fixture_set_version = ?
                ORDER BY sequence
                """,
                this::mapResponse,
                fixtureSetId,
                version));
        return result;
    }

    private Map<String, Object> mapResponse(ResultSet rs, int rowNumber) throws SQLException {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("call_key", rs.getString("call_key"));
        row.put("tool_name", rs.getString("tool_name"));
        row.put("arguments", readJson(rs.getString("arguments")));
        row.put("response_status", rs.getString("response_status"));
        row.put("response", readJson(rs.getString("response")));
        row.put("observed_at", rs.getObject("observed_at"));
        row.put("simulated_latency_ms", rs.getLong("simulated_latency_ms"));
        row.put("sequence", rs.getInt("sequence"));
        return row;
    }

    private Object readJson(String value) throws SQLException {
        try {
            return objectMapper.readTree(value);
        } catch (JsonProcessingException exception) {
            throw new SQLException("invalid JSON stored in tool fixtures", exception);
        }
    }
}
