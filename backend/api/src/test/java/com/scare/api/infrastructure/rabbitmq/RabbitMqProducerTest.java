package com.scare.api.infrastructure.rabbitmq;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.*;

import java.util.concurrent.TimeoutException;
import java.util.function.Consumer;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.AmqpException;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.core.ReturnedMessage;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

class RabbitMqProducerTest {

	private final RabbitTemplate template = mock(RabbitTemplate.class);
	private final RabbitMqProducer producer = new RabbitMqProducer(template);

	private void brokerReplies(Consumer<CorrelationData> reply) {
		willAnswer(inv -> {
			reply.accept(inv.getArgument(3));
			return null;
		}).given(template).convertAndSend(eq(""), eq("request_queue"), eq("m"), any(CorrelationData.class));
	}

	@Test
	void ack_이면_정상_종료한다() {
		brokerReplies(c -> c.getFuture().complete(new CorrelationData.Confirm(true, null)));

		assertThatCode(() -> producer.sendAndConfirm("m")).doesNotThrowAnyException();
	}

	@Test
	void nack_이면_예외를_던진다() {
		brokerReplies(c -> c.getFuture().complete(new CorrelationData.Confirm(false, "nack")));

		assertThatThrownBy(() -> producer.sendAndConfirm("m")).isInstanceOf(AmqpException.class);
	}

	@Test
	void 라우팅되지_않고_반송되면_예외를_던진다() {
		brokerReplies(c -> {
			c.setReturned(new ReturnedMessage(new Message(new byte[0], new MessageProperties()), 312, "NO_ROUTE", "",
				"request_queue"));
			c.getFuture().complete(new CorrelationData.Confirm(true, null));
		});

		assertThatThrownBy(() -> producer.sendAndConfirm("m")).isInstanceOf(AmqpException.class);
	}

	@Test
	void 확인_응답이_오지_않으면_시간_초과로_예외를_던진다() {
		brokerReplies(c -> {
		});

		assertThatThrownBy(() -> producer.sendAndConfirm("m"))
			.isInstanceOf(AmqpException.class)
			.hasCauseInstanceOf(TimeoutException.class);
	}
}
