package com.bdlh.touchstone.data.domain;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;
import java.util.UUID;

public final class RunPayloads {
    private RunPayloads() {}

    public record CreateBatchRequest(
            @NotBlank String name,
            @NotBlank String experimentType,
            @NotNull JsonNode fixedConditions) {}

    public record CreateRunRequest(
            UUID batchId,
            @NotBlank String caseId,
            @Min(1) int caseVersion,
            @NotBlank String variantId,
            @NotBlank String snapshotId,
            @NotBlank String agentMode,
            @NotBlank String contextStrategy,
            @NotBlank String model,
            @NotBlank String gitCommit,
            JsonNode modelConfig) {}

    public record CompleteBatchRequest(@NotBlank String status) {}

    public record ContextItemInput(
            @NotBlank String itemKey,
            @NotBlank String itemType,
            @NotBlank String classification,
            @NotNull JsonNode content,
            String contentRef,
            String sourceId,
            String ownerId,
            String observedAt,
            String validFrom,
            String validTo,
            int priority,
            boolean trusted,
            @Min(0) int rawTokens,
            @NotBlank String contentHash,
            int sequence) {}

    public record ContextDecisionInput(
            @NotBlank String itemKey,
            @NotBlank String action,
            @NotBlank String reason,
            @Min(0) int inputTokens,
            @Min(0) int outputTokens,
            JsonNode outputContent,
            String outputHash,
            String referenceId,
            int decisionOrder) {}

    public record ContextMessageInput(
            @Min(0) int messageOrder,
            @NotBlank String role,
            @NotBlank String content,
            @NotBlank String contentHash,
            @Min(0) int tokens) {}

    public record SaveContextBuildRequest(
            @NotBlank String strategy,
            @NotBlank String tokenizerVersion,
            @NotBlank String compressionVersion,
            @Min(1) int tokenBudget,
            @Min(0) int originalTokens,
            @Min(0) int workingTokens,
            @Min(0) int compressionInputTokens,
            @Min(0) int compressionOutputTokens,
            @Min(0) long durationMs,
            boolean requiredRetained,
            boolean budgetFit,
            boolean referencesValid,
            boolean instructionIsolated,
            @NotBlank String status,
            String errorCode,
            @NotEmpty List<@Valid ContextItemInput> items,
            @NotEmpty List<@Valid ContextDecisionInput> decisions,
            @NotEmpty List<@Valid ContextMessageInput> messages) {}

    public record RunEventInput(
            @Min(0) int sequence,
            @NotBlank String eventType,
            @NotNull JsonNode payload,
            String occurredAt) {}

    public record SaveEventsRequest(@NotEmpty List<@Valid RunEventInput> events) {}

    public record SaveEvaluationRequest(
            @NotBlank String evaluatorVersion,
            boolean validRun,
            @NotBlank String status,
            @NotNull JsonNode checks,
            JsonNode metrics) {}

    public record CompleteRunRequest(
            @NotBlank String status,
            JsonNode output,
            String errorCategory,
            String errorMessage) {}
}
