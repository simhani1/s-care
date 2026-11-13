package com.scare.api.solution.walk.outbox;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import com.scare.api.infrastructure.rabbitmq.RabbitMqProducer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class OutboxRelay {

	private final OutboxRepository outboxRepository;
	private final RabbitMqProducer rabbitMqProducer;

	/*
	 * 스케줄러가 행마다 부르는 단건 발행 함수.
	 * FOR UPDATE 는 스냅샷이 아닌 최신 커밋 값을 읽으므로, 다른 인스턴스가 이미 PUBLISHED 로 커밋한 행은
	 * status 조건에서 빠지고, 아직 커밋 전인 행은 SKIP LOCKED 로 건너뛴다. 이중 발행을 막는 것은 이 행 잠금뿐이다.
	 * 확인 응답을 받은 뒤에만 PUBLISHED 로 바꾸고, 실패하면 예외로 롤백해 행이 PENDING 으로 남는다.
	 * 한 행의 실패가 다른 행의 발행을 되돌리지 않도록 행마다 REQUIRES_NEW 로 연다.
	 */
	@Transactional(propagation = Propagation.REQUIRES_NEW)
	public boolean publish(Long outboxId) {
		Outbox outbox = outboxRepository.lockPending(outboxId).orElse(null);
		if (outbox == null) {
			return false;
		}
		rabbitMqProducer.sendAndConfirm(outbox.getPayload());
		outbox.markPublished();
		log.info("[OutboxRelay] published outboxId={} courseId={}", outboxId, outbox.getWalkingCourseId());
		return true;
	}

}
