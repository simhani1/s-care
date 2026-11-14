package com.scare.api.core.config.security;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.function.Supplier;

import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;
import org.springframework.util.Assert;

public class InternalSecretAuthorizationManager implements AuthorizationManager<RequestAuthorizationContext> {

	public static final String HEADER = "X-Internal-Secret";

	private final byte[] secret;

	public InternalSecretAuthorizationManager(String secret) {
		Assert.hasText(secret, "internal.api.secret must not be blank");
		this.secret = secret.getBytes(StandardCharsets.UTF_8);
	}

	@Override
	public AuthorizationDecision check(Supplier<Authentication> authentication, RequestAuthorizationContext context) {
		String provided = context.getRequest().getHeader(HEADER);
		return new AuthorizationDecision(
			provided != null && MessageDigest.isEqual(secret, provided.getBytes(StandardCharsets.UTF_8)));
	}

}
