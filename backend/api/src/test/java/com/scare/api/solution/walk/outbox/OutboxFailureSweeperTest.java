package com.scare.api.solution.walk.outbox;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.*;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.LongStream;

import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import com.scare.api.solution.walk.repository.WalkingCourseRepository;

class OutboxFailureSweeperTest {

	private final OutboxRepository outboxRepository = mock(OutboxRepository.class);
	private final WalkingCourseRepository courseRepository = mock(WalkingCourseRepository.class);
	private final OutboxFailureSweeper sweeper = new OutboxFailureSweeper(outboxRepository, courseRepository,
		new TransactionTemplate(mock(PlatformTransactionManager.class)));

	private static OutboxRepository.StaleOutbox stale(long id) {
		return new OutboxRepository.StaleOutbox() {
			public Long getId() {
				return id;
			}

			public Long getWalkingCourseId() {
				return id + 1000;
			}
		};
	}

	private static List<OutboxRepository.StaleOutbox> batch(long from, int count) {
		return LongStream.range(from, from + count).mapToObj(OutboxFailureSweeperTest::stale).toList();
	}

	@Test
	void 실패로_바꾼_행의_코스만_실패로_바꾼다() {
		given(outboxRepository.findStalePublished(any(), any())).willReturn(List.of(stale(1), stale(2)));
		given(outboxRepository.failPublished(eq(1L), any(), any())).willReturn(1);
		given(outboxRepository.failPublished(eq(2L), any(), any())).willReturn(0);

		sweeper.failStale();

		then(courseRepository).should().failAnalyzing(eq(1001L), any());
		then(courseRepository).should(never()).failAnalyzing(eq(1002L), any());
	}

	@Test
	void 기준은_한_시간_전이고_후보와_UPDATE_에_같은_기준을_쓴다() {
		given(outboxRepository.findStalePublished(any(), any())).willReturn(List.of(stale(1)));
		given(outboxRepository.failPublished(anyLong(), any(), any())).willReturn(1);
		LocalDateTime before = LocalDateTime.now();

		sweeper.failStale();

		ArgumentCaptor<LocalDateTime> threshold = ArgumentCaptor.forClass(LocalDateTime.class);
		then(outboxRepository).should().findStalePublished(threshold.capture(), any());
		assertThat(Duration.between(threshold.getValue(), before).abs()).isLessThan(Duration.ofHours(1).plusSeconds(1));
		assertThat(Duration.between(threshold.getValue(), before)).isGreaterThanOrEqualTo(Duration.ofMinutes(59));
		then(outboxRepository).should().failPublished(eq(1L), eq(threshold.getValue()), any());
	}

	@Test
	void 배치가_가득_차면_다음_배치를_읽는다() {
		given(outboxRepository.findStalePublished(any(), any())).willReturn(batch(1, 100), batch(101, 3));
		given(outboxRepository.failPublished(anyLong(), any(), any())).willReturn(1);

		sweeper.failStale();

		then(outboxRepository).should(times(2)).findStalePublished(any(), any());
		then(courseRepository).should(times(103)).failAnalyzing(anyLong(), any());
	}
}
