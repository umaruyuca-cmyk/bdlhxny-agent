package com.bdlh.touchstone.data.repository;

import static com.bdlh.touchstone.data.domain.AuthPayloads.*;

import com.bdlh.touchstone.data.domain.AuthException;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

@Repository
public class AuthRepository {
    private static final String DUMMY_BCRYPT =
            "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5Hz8jYb9lDdBa";
    private static final int MAX_FAILED_ATTEMPTS = 5;
    private static final long SESSION_TTL_HOURS = 24;
    private static final int LOCK_MINUTES = 15;

    private final JdbcTemplate jdbc;
    private final ObjectMapper objectMapper;
    private final SecureRandom secureRandom = new SecureRandom();

    public AuthRepository(JdbcTemplate jdbc, ObjectMapper objectMapper) {
        this.jdbc = jdbc;
        this.objectMapper = objectMapper;
    }

    public LoginResponse login(LoginRequest request) {
        Optional<AccountRow> account = findAccount(request.username());

        if (account.isPresent() && "LOCKED".equals(account.get().status())) {
            if (isLocked(account.get())) {
                audit(account.get().id(), "LOGIN", false, "account locked", request.ipAddress());
                throw new AuthException(HttpStatus.LOCKED, "账号已锁定，请稍后再试");
            }
            unlock(account.get().id());
        }

        boolean disabled = account.isPresent() && "DISABLED".equals(account.get().status());
        boolean passwordOk = passwordMatches(request.username(), request.password());

        if (account.isEmpty() || disabled || !passwordOk) {
            account.ifPresent(a -> {
                if (!disabled) {
                    registerFailure(a);
                }
            });
            audit(account.map(AccountRow::id).orElse(null), "LOGIN", false, "invalid credentials",
                    request.ipAddress());
            throw new AuthException(HttpStatus.UNAUTHORIZED, "用户名或密码错误");
        }

        AccountRow a = account.get();
        resetFailure(a.id());
        String token = generateToken();
        String tokenHash = sha256Hex(token);
        String expiresAt = insertSession(a.id(), tokenHash, request.ipAddress(), request.userAgent());
        audit(a.id(), "LOGIN", true, "ok", request.ipAddress());
        return new LoginResponse(a.id(), a.username(), token, expiresAt);
    }

    public VerifyResponse verify(String token) {
        String tokenHash = sha256Hex(token);
        List<AccountRow> rows = jdbc.query(
                """
                SELECT a.id, a.username, a.status, a.failed_attempts, a.locked_until
                FROM touchstone.auth_sessions s
                JOIN touchstone.accounts a ON a.id = s.account_id
                WHERE s.token_hash = ?
                  AND s.revoked_at IS NULL
                  AND s.expires_at > now()
                  AND a.status = 'ACTIVE'
                """,
                this::mapAccount,
                tokenHash);
        if (rows.isEmpty()) {
            throw new AuthException(HttpStatus.UNAUTHORIZED, "会话无效或已过期");
        }
        jdbc.update("UPDATE touchstone.auth_sessions SET last_seen_at = now() WHERE token_hash = ?", tokenHash);
        return new VerifyResponse(rows.get(0).id(), rows.get(0).username());
    }

    public void logout(String token) {
        String tokenHash = sha256Hex(token);
        List<UUID> accounts = jdbc.query(
                "SELECT account_id FROM touchstone.auth_sessions WHERE token_hash = ?",
                (rs, rowNumber) -> rs.getObject("account_id", UUID.class),
                tokenHash);
        jdbc.update(
                "UPDATE touchstone.auth_sessions SET revoked_at = now() WHERE token_hash = ? AND revoked_at IS NULL",
                tokenHash);
        if (!accounts.isEmpty()) {
            audit(accounts.get(0), "LOGOUT", true, "ok", null);
        }
    }

    private Optional<AccountRow> findAccount(String username) {
        return jdbc.query(
                        "SELECT id, username, status, failed_attempts, locked_until "
                                + "FROM touchstone.accounts WHERE username = ?",
                        this::mapAccount,
                        username)
                .stream()
                .findFirst();
    }

    private boolean isLocked(AccountRow account) {
        return account.lockedUntil() != null
                && account.lockedUntil().isAfter(OffsetDateTime.now(ZoneOffset.UTC));
    }

    private void unlock(UUID accountId) {
        jdbc.update(
                """
                UPDATE touchstone.accounts
                SET status = 'ACTIVE', failed_attempts = 0, locked_until = NULL
                WHERE id = ?
                """,
                accountId);
    }

    private boolean passwordMatches(String username, String password) {
        Boolean matches = jdbc.queryForObject(
                """
                SELECT crypt(?, COALESCE((SELECT password_hash FROM touchstone.accounts WHERE username = ?), ?))
                     = COALESCE((SELECT password_hash FROM touchstone.accounts WHERE username = ?), ?)
                """,
                Boolean.class,
                password,
                username,
                DUMMY_BCRYPT,
                username,
                DUMMY_BCRYPT);
        return Boolean.TRUE.equals(matches);
    }

    private void registerFailure(AccountRow account) {
        int failed = account.failedAttempts() + 1;
        if (failed >= MAX_FAILED_ATTEMPTS) {
            jdbc.update(
                    """
                    UPDATE touchstone.accounts
                    SET status = 'LOCKED', failed_attempts = ?,
                        locked_until = now() + make_interval(mins => ?)
                    WHERE id = ?
                    """,
                    failed,
                    LOCK_MINUTES,
                    account.id());
        } else {
            jdbc.update(
                    "UPDATE touchstone.accounts SET failed_attempts = ? WHERE id = ?",
                    failed,
                    account.id());
        }
    }

    private void resetFailure(UUID accountId) {
        jdbc.update(
                """
                UPDATE touchstone.accounts
                SET failed_attempts = 0, locked_until = NULL, last_login_at = now()
                WHERE id = ?
                """,
                accountId);
    }

    private String insertSession(UUID accountId, String tokenHash, String ipAddress, String userAgent) {
        OffsetDateTime expiresAt = OffsetDateTime.now(ZoneOffset.UTC).plusHours(SESSION_TTL_HOURS);
        jdbc.update(
                """
                INSERT INTO touchstone.auth_sessions
                    (id, account_id, token_hash, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                UUID.randomUUID(),
                accountId,
                tokenHash,
                expiresAt,
                ipAddress,
                userAgent);
        return expiresAt.toString();
    }

    private void audit(UUID accountId, String action, boolean succeeded, String reason, String ipAddress) {
        jdbc.update(
                """
                INSERT INTO touchstone.audit_log
                    (id, account_id, action, succeeded, detail, ip_address)
                VALUES (?, ?, ?, ?, ?::jsonb, ?)
                """,
                UUID.randomUUID(),
                accountId,
                action,
                succeeded,
                json(Map.of("reason", reason == null ? "" : reason)),
                ipAddress);
    }

    private String generateToken() {
        byte[] bytes = new byte[32];
        secureRandom.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String sha256Hex(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder hex = new StringBuilder("sha256:");
            for (byte b : hash) {
                hex.append(String.format("%02x", b));
            }
            return hex.toString();
        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException("SHA-256 unavailable", exception);
        }
    }

    private AccountRow mapAccount(java.sql.ResultSet rs, int rowNumber) throws java.sql.SQLException {
        return new AccountRow(
                rs.getObject("id", UUID.class),
                rs.getString("username"),
                rs.getString("status"),
                rs.getInt("failed_attempts"),
                rs.getObject("locked_until", OffsetDateTime.class));
    }

    private String json(Map<String, Object> value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (com.fasterxml.jackson.core.JsonProcessingException exception) {
            throw new IllegalArgumentException("detail is not valid JSON", exception);
        }
    }

    private record AccountRow(
            UUID id, String username, String status, int failedAttempts, OffsetDateTime lockedUntil) {}
}
