package com.scare.api.solution.walk.outbox;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.*;

import java.time.Duration;
import java.time.LocalDateTime;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import com.scare.api.solution.walk.repository.WalkingCourseRepository;

class OutboxFailureSweeperTest {

	private final OutboxRepository outboxRepository = mock(OutboxRepository.class);
	private final WalkingCourseRepository courseRepository = mock(WalkingCourseRepository.class);
	private final OutboxFailureSweeper sweeper = new OutboxFailureSweeper(outboxRepository, courseRepository);

	@Test
	void 한_시간_넘은_행을_실패로_바꾸고_코스도_실패로_바꾼다() {
		given(outboxRepository.failStale(any(), any())).willReturn(2);

		sweeper.failStale();

		ArgumentCaptor<LocalDateTime> threshold = ArgumentCaptor.forClass(LocalDateTime.class);
		ArgumentCaptor<LocalDateTime> now = ArgumentCaptor.forClass(LocalDateTime.class);
		then(outboxRepository).should().failStale(threshold.capture(), now.capture());
		assertThat(Duration.between(threshold.getValue(), now.getValue())).isEqualTo(Duration.ofHours(1));
		then(courseRepository).should().failAnalyzingWithFailedOutbox(now.getValue());
	}

	@Test
	void 실패로_바뀐_행이_없으면_코스를_건드리지_않는다() {
		given(outboxRepository.failStale(any(), any())).willReturn(0);

		sweeper.failStale();

		then(courseRepository).should(never()).failAnalyzingWithFailedOutbox(any());
	}
}
