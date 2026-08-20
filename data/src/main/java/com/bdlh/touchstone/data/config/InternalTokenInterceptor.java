package com.bdlh.touchstone.data.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
public class InternalTokenInterceptor implements HandlerInterceptor {
    private final String expectedToken;

    public InternalTokenInterceptor(@Value("${touchstone.internal-token:}") String expectedToken) {
        this.expectedToken = expectedToken == null ? "" : expectedToken.trim();
    }

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler)
            throws Exception {
        if (expectedToken.isEmpty()) {
            writeError(response, 503, "DATA_INTERNAL_TOKEN is not configured");
            return false;
        }
        String provided = request.getHeader("X-Internal-Token");
        if (provided == null || !constantTimeEquals(provided, expectedToken)) {
            writeError(response, 401, "invalid internal service credential");
            return false;
        }
        return true;
    }

    private static boolean constantTimeEquals(String left, String right) {
        return MessageDigest.isEqual(
                left.getBytes(StandardCharsets.UTF_8),
                right.getBytes(StandardCharsets.UTF_8));
    }

    private static void writeError(HttpServletResponse response, int status, String message)
            throws Exception {
        response.setStatus(status);
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"error\":\"" + message + "\"}");
    }
}
