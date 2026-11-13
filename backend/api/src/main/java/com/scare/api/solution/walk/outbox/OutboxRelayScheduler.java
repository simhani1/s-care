package com.scare.api.solution.walk.outbox;

import java.util.List;

import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import com.scare.api.infrastructure.rabbitmq.RabbitMqProducer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxRelayScheduler {

	private static final int BATCH_SIZE = 100;

	private final OutboxRelay outboxRelay;
	private final OutboxRepository outboxRepository;
	private final RabbitMqProducer rabbitMqProducer;

	/*
	 * 여러 인스턴스가 같은 행을 집어도 OutboxRelay 의 행 잠금이 중복 발행을 막는다.
	 * 배치가 가득 찼고 전부 발행됐으면 쌓인 행이 더 있다고 보고 기다리지 않고 다음 배치로 간다.
	 * 실패나 잠금 충돌이 하나라도 있으면 다음 주기로 미뤄, 계속 실패하는 행 위에서 쉬지 않고 도는 것을 막는다.
	 */
	@Scheduled(fixedDelay = 1000)
	public void relayPending() {
		while (relayBatch() == BATCH_SIZE) {
		}
	}

	private int relayBatch() {
		if (!brokerReachable()) {
			return 0;
		}
		List<Long> ids = outboxRepository.findIdsByStatus(OutboxStatus.PENDING, PageRequest.of(0, BATCH_SIZE));
		int published = 0;
		for (Long id : ids) {
			if (publishQuietly(id)) {
				published++;
			}
		}
		return published;
	}

	/*
	 * 브로커 연결 생성은 CachingConnectionFactory 안에서 직렬화되어, 브로커가 응답하지 않으면 시도마다 대기가 쌓인다.
	 * 이 대기가 행 잠금과 DB 커넥션을 쥔 채 일어나지 않도록 트랜잭션을 열기 전에 연결부터 맺는다.
	 */
	private boolean publishQuietly(Long outboxId) {
		if (!brokerReachable()) {
			return false;
		}
		long started = System.nanoTime();
		try {
			return outboxRelay.publish(outboxId);
		} catch (Exception e) {
			log.warn("[OutboxRelay] publish failed after {}ms, stays pending outboxId={}: {}",
				(System.nanoTime() - started) / 1_000_000, outboxId, e.toString());
			return false;
		}
	}

	private boolean brokerReachable() {
		try {
			rabbitMqProducer.ensureConnection();
			return true;
		} catch (Exception e) {
			log.warn("[OutboxRelay] broker unreachable, rows stay pending: {}", e.toString());
			return false;
		}
	}

}
