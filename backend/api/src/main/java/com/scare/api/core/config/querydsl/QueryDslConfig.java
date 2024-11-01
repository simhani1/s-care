package com.scare.api.core.config.querydsl;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import com.querydsl.jpa.JPQLQueryFactory;
import com.querydsl.jpa.impl.JPAQueryFactory;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;

@Configuration
public class QueryDslConfig {

	@PersistenceContext
	private EntityManager em;

	@Bean
	public JPQLQueryFactory jpqlQueryFactory() {
		return new JPAQueryFactory(em);
	}

}
