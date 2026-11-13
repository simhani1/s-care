package com.scare.api.solution.walk.service.command;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.BDDMockito.*;

import java.time.LocalDateTime;
import java.util.Optional;

import org.junit.jupiter.api.Test;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.scare.api.member.repository.MemberRepository;
import com.scare.api.solution.walk.domain.AnalysisStatus;
import com.scare.api.solution.walk.domain.WalkingCourse;
import com.scare.api.solution.walk.exception.NoWalkingCourseException;
import com.scare.api.solution.walk.outbox.OutboxRepository;
import com.scare.api.solution.walk.repository.WalkingCourseRepository;
import com.scare.api.solution.walk.repository.WalkingDetailRepository;
import com.scare.api.solution.walk.service.command.dto.UpdateBestSectionDto;

class WalkingCommandServiceCompleteAnalysisTest {

	private final WalkingCourseRepository courseRepository = mock(WalkingCourseRepository.class);
	private final OutboxRepository outboxRepository = mock(OutboxRepository.class);
	private final WalkingCommandService service = new WalkingCommandService(mock(MemberRepository.class),
		courseRepository, mock(WalkingDetailRepository.class), outboxRepository, new ObjectMapper());

	private final UpdateBestSectionDto result = UpdateBestSectionDto.builder()
		.courseId(7L).maxStress(40).minStress(10).healingStressAvg(12.5).startIdx(60).endIdx(260).build();

	@Test
	void 조건부_UPDATE_가_1행이면_코스에_결과를_기록하고_완료로_바꾼다() {
		WalkingCourse course = WalkingCourse.builder().build();
		given(outboxRepository.complete(eq(7L), any(LocalDateTime.class))).willReturn(1);
		given(courseRepository.findById(7L)).willReturn(Optional.of(course));

		service.completeAnalysis(result);

		assertThat(course.getAnalysisStatus()).isEqualTo(AnalysisStatus.COMPLETED);
		assertThat(course.getMaxStress()).isEqualTo(40);
		assertThat(course.getEndIdx()).isEqualTo(260);
	}

	@Test
	void 이미_완료된_결과는_코스를_건드리지_않고_정상_종료한다() {
		given(outboxRepository.complete(eq(7L), any(LocalDateTime.class))).willReturn(0);
		given(outboxRepository.existsByWalkingCourseId(7L)).willReturn(true);

		assertThatCode(() -> service.completeAnalysis(result)).doesNotThrowAnyException();
		then(courseRepository).should(never()).findById(any());
	}

	@Test
	void 없는_코스면_예외를_던진다() {
		given(outboxRepository.complete(eq(7L), any(LocalDateTime.class))).willReturn(0);
		given(outboxRepository.existsByWalkingCourseId(7L)).willReturn(false);

		assertThatThrownBy(() -> service.completeAnalysis(result)).isInstanceOf(NoWalkingCourseException.class);
	}
}
