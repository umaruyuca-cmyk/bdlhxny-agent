package com.bdlh.touchstone.data.domain;

import jakarta.validation.constraints.NotBlank;
import java.util.UUID;

public final class AuthPayloads {
    private AuthPayloads() {}

    public record LoginRequest(
            @NotBlank String username,
            @NotBlank String password,
            String ipAddress,
            String userAgent) {}

    public record VerifyRequest(@NotBlank String token) {}

    public record LogoutRequest(@NotBlank String token) {}

    public record LoginResponse(
            UUID accountId, String username, String token, String expiresAt) {}

    public record VerifyResponse(UUID accountId, String username) {}
}
