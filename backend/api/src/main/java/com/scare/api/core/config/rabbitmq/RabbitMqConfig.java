package com.scare.api.core.config.rabbitmq;

import java.time.Duration;

import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.amqp.ConnectionFactoryCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMqConfig {

	public static final String REQUEST_QUEUE = "request_queue";
	public static final String DEAD_LETTER_QUEUE = "request_queue.dlq";

	/*
	 * 워커(backend/fast-api/main.py)도 같은 큐를 선언한다. 인수가 하나라도 다르면 브로커가 재선언을
	 * PRECONDITION_FAILED 로 거부하므로 양쪽 인수를 똑같이 유지한다.
	 */
	@Bean
	public Queue requestQueue() {
		return QueueBuilder.durable(REQUEST_QUEUE)
			.deadLetterExchange("")
			.deadLetterRoutingKey(DEAD_LETTER_QUEUE)
			.build();
	}

	@Bean
	public Queue deadLetterQueue() {
		return QueueBuilder.durable(DEAD_LETTER_QUEUE).build();
	}

	@Bean
	public ConnectionFactoryCustomizer handshakeTimeout(
		@Value("${spring.rabbitmq.connection-timeout}") Duration timeout) {
		return factory -> factory.setHandshakeTimeout((int)timeout.toMillis());
	}
}
