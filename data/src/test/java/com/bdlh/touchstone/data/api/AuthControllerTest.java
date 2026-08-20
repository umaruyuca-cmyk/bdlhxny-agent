package com.bdlh.touchstone.data.api;

import static com.bdlh.touchstone.data.domain.AuthPayloads.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.bdlh.touchstone.data.domain.AuthException;
import com.bdlh.touchstone.data.repository.AuthRepository;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

class AuthControllerTest {
    private AuthRepository repository;
    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        repository = Mockito.mock(AuthRepository.class);
        mvc = MockMvcBuilders.standaloneSetup(new AuthController(repository)).build();
    }

    @Test
    void loginReturnsSessionToken() throws Exception {
        UUID accountId = UUID.randomUUID();
        when(repository.login(any(LoginRequest.class)))
                .thenReturn(new LoginResponse(accountId, "owner", "token-value", "2026-08-21T00:00:00Z"));

        mvc.perform(post("/internal/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"owner\",\"password\":\"secret\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.token").value("token-value"))
                .andExpect(jsonPath("$.username").value("owner"));
    }

    @Test
    void loginRejectsInvalidCredentials() throws Exception {
        when(repository.login(any(LoginRequest.class)))
                .thenThrow(new AuthException(HttpStatus.UNAUTHORIZED, "用户名或密码错误"));

        mvc.perform(post("/internal/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"owner\",\"password\":\"wrong\"}"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.error").value("用户名或密码错误"));
    }

    @Test
    void loginReportsLockedAccount() throws Exception {
        when(repository.login(any(LoginRequest.class)))
                .thenThrow(new AuthException(HttpStatus.LOCKED, "账号已锁定，请稍后再试"));

        mvc.perform(post("/internal/v1/auth/login")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"username\":\"owner\",\"password\":\"secret\"}"))
                .andExpect(status().isLocked())
                .andExpect(jsonPath("$.error").value("账号已锁定，请稍后再试"));
    }

    @Test
    void verifyReturnsAccount() throws Exception {
        UUID accountId = UUID.randomUUID();
        when(repository.verify("token-value"))
                .thenReturn(new VerifyResponse(accountId, "owner"));

        mvc.perform(post("/internal/v1/auth/verify")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"token-value\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.username").value("owner"));
    }

    @Test
    void verifyRejectsUnknownSession() throws Exception {
        when(repository.verify("bad-token"))
                .thenThrow(new AuthException(HttpStatus.UNAUTHORIZED, "会话无效或已过期"));

        mvc.perform(post("/internal/v1/auth/verify")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"bad-token\"}"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void logoutIsIdempotent() throws Exception {
        doThrow(new AuthException(HttpStatus.UNAUTHORIZED, "会话无效或已过期"))
                .when(repository)
                .logout("bad-token");

        mvc.perform(post("/internal/v1/auth/logout")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"token\":\"token-value\"}"))
                .andExpect(status().isNoContent());
    }
}
