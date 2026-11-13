package com.scare.api.solution.walk.outbox;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.support.TransactionTemplate;

import com.scare.api.solution.walk.repository.WalkingCourseRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxFailureSweeper {

	static final Duration THRESHOLD = Duration.ofHours(1);
	static final int BATCH_SIZE = 100;

	private final OutboxRepository outboxRepository;
	private final WalkingCourseRepository walkingCourseRepository;
	private final TransactionTemplate transactionTemplate;

	/*
	 * 후보는 잠그지 않는 일반 SELECT 로 고르고, 바꾸는 행만 PK 로 잠근다. 범위 잠금이 없어 저장의 INSERT 나
	 * 릴레이와 교착되지 않는다. 행마다 짧은 트랜잭션에서 아웃박스, 코스 순(결과 저장과 같은 순서)으로 잠그고,
	 * UPDATE 가 잠금 뒤 최신 커밋 값으로 조건을 다시 평가하므로 그 사이 완료된 행은 1 행을 받지 못해 코스도 건드리지 않는다.
	 * 처리한 후보는 모두 조건에서 빠지므로 다시 고른 배치는 새 행만 담는다.
	 */
	@Scheduled(fixedDelayString = "${outbox.sweep.interval:PT1H}")
	public void failStale() {
		LocalDateTime threshold = LocalDateTime.now().minus(THRESHOLD);
		List<OutboxRepository.StaleOutbox> batch;
		int failed = 0;
		do {
			batch = outboxRepository.findStalePublished(threshold, PageRequest.of(0, BATCH_SIZE));
			for (OutboxRepository.StaleOutbox outbox : batch) {
				if (Boolean.TRUE.equals(transactionTemplate.execute(status -> failOne(outbox, threshold)))) {
					failed++;
				}
			}
		} while (batch.size() == BATCH_SIZE);
		if (failed > 0) {
			log.warn("[OutboxFailureSweeper] published but not completed within {}, marked failed count={}",
				THRESHOLD, failed);
		}
	}

	private boolean failOne(OutboxRepository.StaleOutbox outbox, LocalDateTime threshold) {
		LocalDateTime now = LocalDateTime.now();
		if (outboxRepository.failPublished(outbox.getId(), threshold, now) == 0) {
			return false;
		}
		walkingCourseRepository.failAnalyzing(outbox.getWalkingCourseId(), now);
		return true;
	}

}
