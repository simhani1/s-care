package com.scare.api.solution.walk.outbox;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.*;

import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.AmqpException;

import com.scare.api.infrastructure.rabbitmq.RabbitMqProducer;

class OutboxRelayTest {

	private final OutboxRepository repository = mock(OutboxRepository.class);
	private final RabbitMqProducer producer = mock(RabbitMqProducer.class);
	private final OutboxRelay relay = new OutboxRelay(repository, producer);

	private final Outbox outbox = Outbox.builder().walkingCourseId(7L).payload("{\"courseId\":7}").build();

	@Test
	void 잠금을_얻지_못하면_발행하지_않는다() {
		given(repository.lockPending(1L)).willReturn(Optional.empty());

		assertThat(relay.publish(1L)).isFalse();
		then(producer).should(never()).sendAndConfirm(any());
	}

	@Test
	void 확인_응답을_받으면_발행됨으로_바꾼다() {
		given(repository.lockPending(1L)).willReturn(Optional.of(outbox));

		assertThat(relay.publish(1L)).isTrue();
		then(producer).should().sendAndConfirm("{\"courseId\":7}");
		assertThat(outbox.getStatus()).isEqualTo(OutboxStatus.PUBLISHED);
	}

	@Test
	void 확인_응답이_실패하면_발행_대기로_남는다() {
		given(repository.lockPending(1L)).willReturn(Optional.of(outbox));
		willThrow(new AmqpException("nack")).given(producer).sendAndConfirm(any());

		assertThatThrownBy(() -> relay.publish(1L)).isInstanceOf(AmqpException.class);
		assertThat(outbox.getStatus()).isEqualTo(OutboxStatus.PENDING);
	}
}
