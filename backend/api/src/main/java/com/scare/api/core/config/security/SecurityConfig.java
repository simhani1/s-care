package com.scare.api.core.config.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.scare.api.core.jwt.filter.JWTFilter;
import com.scare.api.core.jwt.util.JWTUtil;
import com.scare.api.member.domain.MemberRole;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;

@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

	private final JWTUtil jwtUtil;
	private final ObjectMapper objectMapper;

	@Value("${springdoc.swagger-ui.path}")
	private String swaggerPath;
	private String fullSwaggerPath;

	@Value("${internal.api.secret}")
	private String internalApiSecret;

	@Value("${springdoc.api-docs.path}")
	private String apiDocsPath;
	private String fullApiDocsPath;

	@PostConstruct
	private void init() {
		this.fullSwaggerPath = swaggerPath + "/**";
		this.fullApiDocsPath = apiDocsPath + "/**";
	}

	@Bean
	public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
		// CSRF 보호 비활성화
		http.csrf(AbstractHttpConfigurer::disable);

		// 기본 설정인 Session 방식은 사용하지 않고 JWT 방식을 사용하기 위한 설정
		http.sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS));

		http.authorizeHttpRequests(auth -> auth
			.requestMatchers("/api/v1/members/auth/login", "/api/v1/members/auth/reissue").permitAll()
			.requestMatchers(fullSwaggerPath, fullApiDocsPath).permitAll()
			.requestMatchers("/internal/**").access(new InternalSecretAuthorizationManager(internalApiSecret))
			.requestMatchers("/api/v*/**").hasAuthority(MemberRole.ROLE_USER.name())
			.requestMatchers("/error").permitAll()
			.anyRequest().authenticated());

		http.addFilterBefore(new JWTFilter(jwtUtil, objectMapper), UsernamePasswordAuthenticationFilter.class);

		return http.build();
	}

}
