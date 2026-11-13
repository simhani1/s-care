package com.scare.api.solution.walk.outbox;

import java.time.Duration;
import java.time.LocalDateTime;

import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import com.scare.api.solution.walk.repository.WalkingCourseRepository;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxFailureSweeper {

	static final Duration THRESHOLD = Duration.ofHours(1);

	private final OutboxRepository outboxRepository;
	private final WalkingCourseRepository walkingCourseRepository;

	/*
	 * 두 UPDATE 모두 잠금을 잡은 뒤 최신 커밋 값으로 조건을 다시 평가한다. 결과 저장이 아웃박스 행을 먼저 잠갔다면
	 * 여기서 기다렸다가 COMPLETED 를 보고 건너뛰므로, 동시에 완료된 행이 FAILED 로 덮이지 않는다.
	 * 잠금 순서는 결과 저장과 같은 아웃박스, 코스 순이다.
	 * PENDING 도 대상이라 영구히 발행에 실패하는 행이 릴레이의 하위 id 배치를 최대 THRESHOLD 동안만 막는다.
	 * PENDING 행의 updated_at 은 생성 시각, PUBLISHED 행의 updated_at 은 발행 시각이다.
	 */
	@Scheduled(fixedDelayString = "${outbox.sweep.interval:PT1H}")
	@Transactional
	public void failStale() {
		LocalDateTime now = LocalDateTime.now();
		int outboxes = outboxRepository.failStale(now.minus(THRESHOLD), now);
		if (outboxes == 0) {
			return;
		}
		int courses = walkingCourseRepository.failAnalyzingWithFailedOutbox(now);
		log.warn("[OutboxFailureSweeper] not completed within {}, marked failed outbox={} course={}",
			THRESHOLD, outboxes, courses);
	}

}
