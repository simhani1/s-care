package com.scare.api.core.config.security;

import static org.assertj.core.api.Assertions.*;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;

class InternalSecretAuthorizationManagerTest {

	private final InternalSecretAuthorizationManager manager = new InternalSecretAuthorizationManager("s3cret");

	private boolean granted(String header) {
		MockHttpServletRequest request = new MockHttpServletRequest("PUT", "/internal/v1/walking/1/analysis-result");
		if (header != null) {
			request.addHeader(InternalSecretAuthorizationManager.HEADER, header);
		}
		return manager.check(() -> null, new RequestAuthorizationContext(request)).isGranted();
	}

	@Test
	void 비밀이_일치할_때만_허용한다() {
		assertThat(granted("s3cret")).isTrue();
		assertThat(granted(null)).isFalse();
		assertThat(granted("")).isFalse();
		assertThat(granted("s3cre")).isFalse();
		assertThat(granted("s3cret ")).isFalse();
	}

	@Test
	void 빈_비밀로는_만들_수_없다() {
		assertThatThrownBy(() -> new InternalSecretAuthorizationManager(" "))
			.isInstanceOf(IllegalArgumentException.class);
	}
}
