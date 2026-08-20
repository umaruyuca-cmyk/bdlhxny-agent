package com.bdlh.touchstone.data.repository;

import static com.bdlh.touchstone.data.domain.RunPayloads.*;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
public class RunRepository {
    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;

    public RunRepository(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    public UUID createBatch(CreateBatchRequest request) {
        UUID id = UUID.randomUUID();
        jdbc.update(
                """
                INSERT INTO touchstone.run_batches
                    (id, name, experiment_type, fixed_conditions, status)
                VALUES (?, ?, ?, ?::jsonb, 'RUNNING')
                """,
                id,
                request.name(),
                request.experimentType(),
                json(request.fixedConditions()));
        return id;
    }

    public UUID createRun(CreateRunRequest request) {
        UUID id = UUID.randomUUID();
        jdbc.update(
                """
                INSERT INTO touchstone.agent_runs
                    (id, batch_id, case_id, case_version, variant_id, snapshot_id,
                     agent_mode, context_strategy, model, model_config, git_commit, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, 'CREATED')
                """,
                id,
                request.batchId(),
                request.caseId(),
                request.caseVersion(),
                request.variantId(),
                request.snapshotId(),
                request.agentMode(),
                request.contextStrategy(),
                request.model(),
                jsonOrEmpty(request.modelConfig()),
                request.gitCommit());
        return id;
    }

    public void completeBatch(UUID batchId, CompleteBatchRequest request) {
        if (!List.of("COMPLETE", "FAILED", "CANCELLED").contains(request.status())) {
            throw new IllegalArgumentException("invalid terminal batch status: " + request.status());
        }
        int updated = jdbc.update(
                """
                UPDATE touchstone.run_batches
                SET status = ?, completed_at = now()
                WHERE id = ?
                """,
                request.status(),
                batchId);
        if (updated == 0) {
            throw new IllegalArgumentException("unknown batch_id: " + batchId);
        }
    }

    public Map<String, Object> getBatch(UUID batchId) {
        Map<String, Object> batch = jdbc.queryForObject(
                """
                SELECT id, name, experiment_type, fixed_conditions::text AS fixed_conditions,
                       status, created_at, completed_at
                FROM touchstone.run_batches WHERE id = ?
                """,
                (rs, rowNumber) -> {
                    Map<String, Object> row = new LinkedHashMap<>();
                    row.put("id", rs.getObject("id"));
                    row.put("name", rs.getString("name"));
                    row.put("experimentType", rs.getString("experiment_type"));
                    try {
                        row.put("fixedConditions", objectMapper.readTree(rs.getString("fixed_conditions")));
                    } catch (JsonProcessingException exception) {
                        throw new java.sql.SQLException("invalid batch fixed_conditions JSON", exception);
                    }
                    row.put("status", rs.getString("status"));
                    row.put("createdAt", rs.getObject("created_at"));
                    row.put("completedAt", rs.getObject("completed_at"));
                    return row;
                },
                batchId);
        batch.put(
                "runs",
                jdbc.queryForList(
                        """
                        SELECT id, case_id, case_version, variant_id, agent_mode,
                               context_strategy, model, status, error_category,
                               created_at, completed_at
                        FROM touchstone.agent_runs
                        WHERE batch_id = ?
                        ORDER BY case_id, agent_mode
                        """,
                        batchId));
        return batch;
    }

    @Transactional
    public UUID saveContextBuild(UUID runId, SaveContextBuildRequest request) {
        UUID buildId = UUID.randomUUID();
        jdbc.update(
                """
                INSERT INTO touchstone.context_builds
                    (id, run_id, strategy, tokenizer_version, compression_version,
                     token_budget, original_tokens, working_tokens,
                     compression_input_tokens, compression_output_tokens, duration_ms,
                     required_retained, budget_fit, references_valid, instruction_isolated,
                     status, error_code)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                buildId,
                runId,
                request.strategy(),
                request.tokenizerVersion(),
                request.compressionVersion(),
                request.tokenBudget(),
                request.originalTokens(),
                request.workingTokens(),
                request.compressionInputTokens(),
                request.compressionOutputTokens(),
                request.durationMs(),
                request.requiredRetained(),
                request.budgetFit(),
                request.referencesValid(),
                request.instructionIsolated(),
                request.status(),
                request.errorCode());

        for (ContextItemInput item : request.items()) {
            jdbc.update(
                    """
                    INSERT INTO touchstone.context_items
                        (id, context_build_id, item_key, item_type, classification,
                         content, content_ref, source_id, owner_id, observed_at,
                         valid_from, valid_to, priority, trusted, raw_tokens,
                         content_hash, sequence)
                    VALUES (?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    UUID.randomUUID(),
                    buildId,
                    item.itemKey(),
                    item.itemType(),
                    item.classification(),
                    json(item.content()),
                    item.contentRef(),
                    item.sourceId(),
                    item.ownerId(),
                    item.observedAt(),
                    item.validFrom(),
                    item.validTo(),
                    item.priority(),
                    item.trusted(),
                    item.rawTokens(),
                    item.contentHash(),
                    item.sequence());
        }

        for (ContextDecisionInput decision : request.decisions()) {
            jdbc.update(
                    """
                    INSERT INTO touchstone.context_decisions
                        (id, context_build_id, item_key, action, reason,
                         input_tokens, output_tokens, output_content, output_hash,
                         reference_id, decision_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?::jsonb, ?, ?, ?)
                    """,
                    UUID.randomUUID(),
                    buildId,
                    decision.itemKey(),
                    decision.action(),
                    decision.reason(),
                    decision.inputTokens(),
                    decision.outputTokens(),
                    jsonOrNull(decision.outputContent()),
                    decision.outputHash(),
                    decision.referenceId(),
                    decision.decisionOrder());
        }

        for (ContextMessageInput message : request.messages()) {
            jdbc.update(
                    """
                    INSERT INTO touchstone.context_messages
                        (id, context_build_id, message_order, role, content,
                         content_hash, tokens)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    UUID.randomUUID(),
                    buildId,
                    message.messageOrder(),
                    message.role(),
                    message.content(),
                    message.contentHash(),
                    message.tokens());
        }
        return buildId;
    }

    @Transactional
    public void saveEvents(UUID runId, SaveEventsRequest request) {
        for (RunEventInput event : request.events()) {
            jdbc.update(
                    """
                    INSERT INTO touchstone.run_events
                        (id, run_id, sequence, event_type, payload, occurred_at)
                    VALUES (?, ?, ?, ?, ?::jsonb, COALESCE(?::timestamptz, now()))
                    """,
                    UUID.randomUUID(),
                    runId,
                    event.sequence(),
                    event.eventType(),
                    json(event.payload()),
                    event.occurredAt());
        }
    }

    public void saveEvaluation(UUID runId, SaveEvaluationRequest request) {
        jdbc.update(
                """
                INSERT INTO touchstone.evaluation_results
                    (id, run_id, evaluator_version, valid_run, status, checks, metrics)
                VALUES (?, ?, ?, ?, ?, ?::jsonb, ?::jsonb)
                ON CONFLICT (run_id) DO UPDATE SET
                    evaluator_version = EXCLUDED.evaluator_version,
                    valid_run = EXCLUDED.valid_run,
                    status = EXCLUDED.status,
                    checks = EXCLUDED.checks,
                    metrics = EXCLUDED.metrics,
                    created_at = now()
                """,
                UUID.randomUUID(),
                runId,
                request.evaluatorVersion(),
                request.validRun(),
                request.status(),
                json(request.checks()),
                jsonOrEmpty(request.metrics()));
    }

    public void complete(UUID runId, CompleteRunRequest request) {
        int updated = jdbc.update(
                """
                UPDATE touchstone.agent_runs
                SET status = ?, output = ?::jsonb, error_category = ?,
                    error_message = ?, completed_at = now()
                WHERE id = ?
                """,
                request.status(),
                jsonOrEmpty(request.output()),
                request.errorCategory(),
                request.errorMessage(),
                runId);
        if (updated == 0) {
            throw new IllegalArgumentException("unknown run_id: " + runId);
        }
    }

    public Map<String, Object> getRun(UUID runId) {
        Map<String, Object> run = new LinkedHashMap<>(jdbc.queryForMap(
                """
                SELECT id, batch_id, case_id, case_version, variant_id, snapshot_id,
                       agent_mode, context_strategy, model, model_config, git_commit,
                       status, output, error_category, error_message,
                       created_at, completed_at
                FROM touchstone.agent_runs WHERE id = ?
                """,
                runId));
        List<Map<String, Object>> builds = jdbc.queryForList(
                """
                SELECT id, strategy, tokenizer_version, compression_version,
                       token_budget, original_tokens, working_tokens, duration_ms,
                       required_retained, budget_fit, references_valid,
                       instruction_isolated, status, error_code, created_at
                FROM touchstone.context_builds
                WHERE run_id = ? ORDER BY created_at
                """,
                runId);
        run.put("contextBuilds", builds);
        return run;
    }

    private String json(JsonNode node) {
        try {
            return objectMapper.writeValueAsString(node);
        } catch (JsonProcessingException exception) {
            throw new IllegalArgumentException("payload is not valid JSON", exception);
        }
    }

    private String jsonOrEmpty(JsonNode node) {
        return node == null ? "{}" : json(node);
    }

    private String jsonOrNull(JsonNode node) {
        return node == null ? "null" : json(node);
    }
}
