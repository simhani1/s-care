package com.scare.api.solution.walk.outbox;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.*;

import java.util.List;
import java.util.stream.LongStream;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.AmqpException;

import com.scare.api.infrastructure.rabbitmq.RabbitMqProducer;

class OutboxRelaySchedulerTest {

	private final OutboxRelay relay = mock(OutboxRelay.class);
	private final OutboxRepository repository = mock(OutboxRepository.class);
	private final RabbitMqProducer producer = mock(RabbitMqProducer.class);
	private final OutboxRelayScheduler scheduler = new OutboxRelayScheduler(relay, repository, producer);

	private static List<Long> ids(long from, int count) {
		return LongStream.range(from, from + count).boxed().toList();
	}

	@Test
	void 가득_찬_배치를_모두_발행하면_기다리지_않고_다음_배치로_간다() {
		given(repository.findIdsByStatus(eq(OutboxStatus.PENDING), any()))
			.willReturn(ids(1, 100), ids(101, 100), ids(201, 5));
		given(relay.publish(anyLong())).willReturn(true);

		scheduler.relayPending();

		then(repository).should(times(3)).findIdsByStatus(eq(OutboxStatus.PENDING), any());
		then(relay).should(times(205)).publish(anyLong());
	}

	@Test
	void 한_행이_실패해도_나머지는_발행하고_이번_주기를_끝낸다() {
		given(repository.findIdsByStatus(eq(OutboxStatus.PENDING), any())).willReturn(ids(1, 100));
		given(relay.publish(anyLong())).willReturn(true);
		given(relay.publish(50L)).willThrow(new AmqpException("nack"));

		scheduler.relayPending();

		then(repository).should(times(1)).findIdsByStatus(eq(OutboxStatus.PENDING), any());
		then(relay).should(times(100)).publish(anyLong());
	}

	@Test
	void 브로커에_연결할_수_없으면_DB_를_읽지_않는다() {
		willThrow(new AmqpException("down")).given(producer).ensureConnection();

		scheduler.relayPending();

		then(repository).shouldHaveNoInteractions();
		then(relay).shouldHaveNoInteractions();
	}
}
