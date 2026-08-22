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
public class ToolCatalogRepository {
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public ToolCatalogRepository(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    public Map<String, Object> loadCatalog() {
        Map<String, Object> catalog = new LinkedHashMap<>();
        catalog.put("operations", jdbc.queryForList(
                "SELECT code, description FROM touchstone.tool_operations ORDER BY code"));
        catalog.put("toolsets", jdbc.queryForList(
                "SELECT name, description FROM touchstone.toolsets ORDER BY name"));
        catalog.put("capabilities", jdbc.query(
                """
                SELECT name, description, domain, adapter, read_only,
                       requires_authenticated_user, required_arguments::text AS required_arguments,
                       depends_on::text AS depends_on, timeout_seconds, enabled,
                       operations::text AS operations, toolsets::text AS toolsets,
                       side_effect, requires_confirmation, risk_level
                FROM touchstone.tool_capabilities
                ORDER BY name
                """,
                this::mapCapability));
        catalog.put("skills", loadSkills());
        return catalog;
    }

    private List<Map<String, Object>> loadSkills() {
        List<Map<String, Object>> skills = jdbc.queryForList(
                """
                SELECT skill_id, skill_version, domain, status, enabled
                FROM touchstone.tool_skills
                ORDER BY skill_id
                """);
        for (Map<String, Object> skill : skills) {
            String skillId = (String) skill.get("skill_id");
            skill.put("operations", jdbc.queryForList(
                    """
                    SELECT code, required
                    FROM touchstone.tool_skill_operations
                    WHERE skill_id = ?
                    ORDER BY code
                    """,
                    skillId));
            skill.put("capabilities", jdbc.queryForList(
                    """
                    SELECT capability, required
                    FROM touchstone.tool_skill_capabilities
                    WHERE skill_id = ?
                    ORDER BY capability
                    """,
                    skillId));
        }
        return skills;
    }

    private Map<String, Object> mapCapability(ResultSet rs, int rowNumber) throws SQLException {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("name", rs.getString("name"));
        row.put("description", rs.getString("description"));
        row.put("domain", rs.getString("domain"));
        row.put("adapter", rs.getString("adapter"));
        row.put("read_only", rs.getBoolean("read_only"));
        row.put("requires_authenticated_user", rs.getBoolean("requires_authenticated_user"));
        row.put("required_arguments", readJson(rs.getString("required_arguments")));
        row.put("depends_on", readJson(rs.getString("depends_on")));
        row.put("timeout_seconds", rs.getInt("timeout_seconds"));
        row.put("enabled", rs.getBoolean("enabled"));
        row.put("operations", readJson(rs.getString("operations")));
        row.put("toolsets", readJson(rs.getString("toolsets")));
        // GT-6 评测轴三列:判官(未确认写入率等)经目录 payload 透出
        row.put("side_effect", rs.getString("side_effect"));
        row.put("requires_confirmation", rs.getBoolean("requires_confirmation"));
        row.put("risk_level", rs.getString("risk_level"));
        return row;
    }

    private Object readJson(String value) throws SQLException {
        try {
            return objectMapper.readTree(value);
        } catch (JsonProcessingException exception) {
            throw new SQLException("invalid JSON stored in tool catalog", exception);
        }
    }
}
