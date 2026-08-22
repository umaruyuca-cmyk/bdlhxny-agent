package com.bdlh.touchstone.data.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

class InternalTokenInterceptorTest {
    @Test
    void failsClosedWhenTokenIsNotConfigured() throws Exception {
        var response = new MockHttpServletResponse();

        boolean accepted = new InternalTokenInterceptor("")
                .preHandle(new MockHttpServletRequest(), response, new Object());

        assertThat(accepted).isFalse();
        assertThat(response.getStatus()).isEqualTo(503);
    }

    @Test
    void acceptsOnlyTheConfiguredInternalToken() throws Exception {
        var interceptor = new InternalTokenInterceptor("service-secret");
        var rejected = new MockHttpServletResponse();

        assertThat(interceptor.preHandle(new MockHttpServletRequest(), rejected, new Object()))
                .isFalse();
        assertThat(rejected.getStatus()).isEqualTo(401);

        var request = new MockHttpServletRequest();
        request.addHeader("X-Internal-Token", "service-secret");
        assertThat(interceptor.preHandle(request, new MockHttpServletResponse(), new Object()))
                .isTrue();
    }
}
