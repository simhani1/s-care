package com.scare.api.core.config.rabbitmq;

import java.time.Duration;

import org.springframework.amqp.core.Queue;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.amqp.ConnectionFactoryCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMqConfig {

	@Bean
	public Queue requestQueue() {
		return new Queue("request_queue");
	}

	@Bean
	public Queue responseQueue() {
		return new Queue("response_queue");
	}

	@Bean
	public ConnectionFactoryCustomizer handshakeTimeout(
		@Value("${spring.rabbitmq.connection-timeout}") Duration timeout) {
		return factory -> factory.setHandshakeTimeout((int)timeout.toMillis());
	}
}

