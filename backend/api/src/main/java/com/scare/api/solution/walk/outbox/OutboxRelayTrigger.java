package com.scare.api.solution.walk.outbox;

import java.time.LocalDateTime;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.event.TransactionPhase;
import org.springframework.transaction.event.TransactionalEventListener;

import com.scare.api.infrastructure.rabbitmq.RabbitMqProducer;

import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxRelayTrigger {

	private static final long STALE_SECONDS = 10;
	private static final int BATCH_SIZE = 100;
	private static final int RELAY_THREADS = 2;
	private static final int RELAY_QUEUE = 100;

	private final OutboxRelay outboxRelay;
	private final OutboxRepository outboxRepository;
	private final RabbitMqProducer rabbitMqProducer;

	/*
	 * 요청 스레드는 저장 트랜잭션의 커넥션을 쥔 채 AFTER_COMMIT 을 실행하므로, 여기서 REQUIRES_NEW 를 열면
	 * 요청 하나가 커넥션 두 개를 요구해 풀이 교착된다. 발행은 별도 스레드로 넘기고 요청 스레드는 곧바로 반환한다.
	 * 릴레이가 동시에 쥐는 커넥션은 이 스레드 수와 스케줄러 스레드 하나를 더한 값으로 묶인다.
	 * 큐가 차면 버린다. 버려진 행은 PENDING 으로 남아 스케줄러가 수거한다.
	 */
	private final ThreadPoolExecutor relayExecutor = new ThreadPoolExecutor(RELAY_THREADS, RELAY_THREADS,
		0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(RELAY_QUEUE),
		Thread.ofPlatform().name("outbox-relay-", 0).factory(),
		(task, executor) -> log.debug("[OutboxRelay] relay queue full, left for scheduler"));

	@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
	public void onSaved(OutboxSavedEvent event) {
		relayExecutor.execute(() -> publishQuietly(event.outboxId()));
	}

	/*
	 * 생성 시각은 JPA auditing 이 JVM 시계로 넣으므로 기준 시각도 DB NOW() 가 아닌 JVM 시계로 계산한다.
	 * 즉시 경로가 아직 처리 중인 행과 겹쳐도 OutboxRelay 의 행 잠금이 중복 발행을 막는다.
	 */
	@Scheduled(fixedDelay = 5000)
	public void relayStale() {
		if (!brokerReachable()) {
			return;
		}
		LocalDateTime before = LocalDateTime.now().minusSeconds(STALE_SECONDS);
		outboxRepository.findIdsByStatusCreatedBefore(OutboxStatus.PENDING, before, PageRequest.of(0, BATCH_SIZE))
			.forEach(this::publishQuietly);
	}

	@PreDestroy
	void shutdown() {
		relayExecutor.shutdownNow();
	}

	/*
	 * 브로커 연결 생성은 CachingConnectionFactory 안에서 직렬화되어, 브로커가 응답하지 않으면 시도마다 대기가 쌓인다.
	 * 이 대기가 행 잠금과 DB 커넥션을 쥔 채 일어나지 않도록 트랜잭션을 열기 전에 연결부터 맺는다.
	 */
	private void publishQuietly(Long outboxId) {
		if (!brokerReachable()) {
			return;
		}
		long started = System.nanoTime();
		try {
			outboxRelay.publish(outboxId);
		} catch (Exception e) {
			log.warn("[OutboxRelay] publish failed after {}ms, stays pending outboxId={}: {}",
				(System.nanoTime() - started) / 1_000_000, outboxId, e.toString());
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
