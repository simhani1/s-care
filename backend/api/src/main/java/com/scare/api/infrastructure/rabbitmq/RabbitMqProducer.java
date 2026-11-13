package com.scare.api.infrastructure.rabbitmq;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

import org.springframework.amqp.AmqpException;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.stereotype.Component;

import lombok.RequiredArgsConstructor;

@Component
@RequiredArgsConstructor
public final class RabbitMqProducer {

	private static final String REQUEST_QUEUE = "request_queue";
	private static final Duration CONFIRM_TIMEOUT = Duration.ofSeconds(3);

	private final RabbitTemplate rabbitTemplate;

	public void ensureConnection() {
		rabbitTemplate.getConnectionFactory().createConnection().close();
	}

	public void sendAndConfirm(String message) {
		CorrelationData correlation = new CorrelationData();
		rabbitTemplate.convertAndSend("", REQUEST_QUEUE, message, correlation);
		CorrelationData.Confirm confirm;
		try {
			confirm = correlation.getFuture().get(CONFIRM_TIMEOUT.toMillis(), TimeUnit.MILLISECONDS);
		} catch (InterruptedException e) {
			Thread.currentThread().interrupt();
			throw new AmqpException("publisher confirm interrupted", e);
		} catch (Exception e) {
			throw new AmqpException("publisher confirm not received", e);
		}
		if (!confirm.isAck()) {
			throw new AmqpException("publisher confirm nack: " + confirm.getReason());
		}
		if (correlation.getReturned() != null) {
			throw new AmqpException("message returned unroutable: " + correlation.getReturned().getReplyText());
		}
	}
}
