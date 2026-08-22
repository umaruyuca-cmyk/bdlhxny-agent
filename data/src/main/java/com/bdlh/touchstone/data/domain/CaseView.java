package com.bdlh.touchstone.data.domain;

import com.fasterxml.jackson.databind.JsonNode;

public record CaseView(
        String id,
        int version,
        String title,
        String message,
        String scene,
        boolean authenticated,
        JsonNode allowedTools,
        String contextProfile,
        int tokenBudget,
        JsonNode expectedChecks,
        boolean publicCase,
        JsonNode steps,
        JsonNode variants) {}
