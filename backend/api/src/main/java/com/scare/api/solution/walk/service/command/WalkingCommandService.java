package com.scare.api.solution.walk.service.command;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.scare.api.member.domain.Member;
import com.scare.api.member.repository.MemberRepository;
import com.scare.api.member.service.helper.MemberServiceHelper;
import com.scare.api.solution.walk.domain.WalkingCourse;
import com.scare.api.solution.walk.domain.WalkingDetail;
import com.scare.api.solution.walk.exception.InvalidAnalysisResultException;
import com.scare.api.solution.walk.exception.NoWalkingCourseException;
import com.scare.api.solution.walk.exception.WalkingCourseDataSaveException;
import com.scare.api.solution.walk.outbox.Outbox;
import com.scare.api.solution.walk.outbox.OutboxRepository;
import com.scare.api.solution.walk.repository.WalkingCourseRepository;
import com.scare.api.solution.walk.repository.WalkingDetailRepository;
import com.scare.api.solution.walk.service.command.dto.SaveWalkingCourseDto;
import com.scare.api.solution.walk.service.command.dto.SaveWalkingCourseLocationDto;
import com.scare.api.solution.walk.service.command.dto.UpdateBestSectionDto;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@Transactional
@RequiredArgsConstructor
public class WalkingCommandService {

	private final MemberRepository memberRepository;
	private final WalkingCourseRepository walkingCourseRepository;
	private final WalkingDetailRepository walkingDetailRepository;
	private final OutboxRepository outboxRepository;
	private final ObjectMapper objectMapper;

	public Long saveWalkingCourse(Long memberId, SaveWalkingCourseDto dto) {
		log.info("[WalkingCommandService] 산책 코스 저장 시작, 산책 시간");
		Member member = MemberServiceHelper.findExistingMember(memberRepository, memberId);
		long walkingTime = getWalkingTime(dto.getStartedAt(), dto.getFinishedAt());

		List<Double> heartRates = dto.getHeartRates();
		List<SaveWalkingCourseLocationDto> walkingLocations = dto.getLocations();

		// 두 리스트 중 더 짧은 길이 계산
		int minSize = Math.min(heartRates.size(), walkingLocations.size());
		heartRates = heartRates.subList(0, minSize);
		walkingLocations = walkingLocations.subList(0, minSize);
		List<WalkingDetail.LocationPoint> locationPoints = processLocationData(walkingLocations);
		Long courseId = saveWithoutStressData(dto, member, locationPoints);
		outboxRepository.save(Outbox.builder()
			.walkingCourseId(courseId)
			.payload(analysisRequestPayload(courseId, walkingTime, heartRates))
			.build());
		return courseId;
	}

	private String analysisRequestPayload(Long courseId, long walkingTime, List<Double> heartRates) {
		try {
			return objectMapper.writeValueAsString(Map.of(
				"courseId", courseId,
				"heartRates", heartRates,
				"walkingTime", walkingTime
			));
		} catch (JsonProcessingException e) {
			throw new WalkingCourseDataSaveException();
		}
	}

	private long getWalkingTime(LocalDateTime startedAt, LocalDateTime finishedAt) {
		return ChronoUnit.SECONDS.between(startedAt, finishedAt);
	}

	private Long saveWithoutStressData(SaveWalkingCourseDto dto,
		Member member, List<WalkingDetail.LocationPoint> locationPoints) {
		Long walkingCourseId = walkingCourseRepository.save(
			createWalkingCourseWthoutStressData(dto, member)).getId();
		walkingDetailRepository.save(createWalkingCourseDetail(walkingCourseId, locationPoints));
		log.info("[WalkingCommandService] 기본 데이터만 산책 코스 저장 성공");

		return walkingCourseId;
	}

	private List<WalkingDetail.LocationPoint> processLocationData(List<SaveWalkingCourseLocationDto> locationPoints) {
		return locationPoints.stream()
			.map(location -> WalkingDetail.LocationPoint.builder()
				.latitude(location.getLatitude())
				.longitude(location.getLongitude())
				.build())
			.collect(Collectors.toList());
	}

	private WalkingCourse createWalkingCourseWithStressData(SaveWalkingCourseDto dto, Member member) {
		return WalkingCourse.builder()
			.minStress(dto.getStressData().getMinStress())
			.maxStress(dto.getStressData().getMaxStress())
			.startIdx(dto.getStressData().getStartIdx() != null ? dto.getStressData().getStartIdx() : 0)
			.endIdx(dto.getStressData().getEndIdx() != null ? dto.getStressData().getEndIdx() : 0)
			.healingStressAvg(
				dto.getStressData().getHealingStressAvg() != null ? dto.getStressData().getHealingStressAvg() : 0)
			.startedAt(dto.getStartedAt())
			.finishedAt(dto.getFinishedAt())
			.member(member)
			.build();
	}

	private WalkingCourse createWalkingCourseWthoutStressData(SaveWalkingCourseDto dto, Member member) {
		return WalkingCourse.builder()
			.startedAt(dto.getStartedAt())
			.finishedAt(dto.getFinishedAt())
			.member(member)
			.build();
	}

	private WalkingDetail createWalkingCourseDetail(Long walkingCourseId,
		List<WalkingDetail.LocationPoint> locationPoints) {
		return WalkingDetail.builder()
			.id(walkingCourseId)
			.locationData(locationPoints)
			.build();
	}

	/*
	 * 조건부 UPDATE 가 아웃박스 행을 잠그고 최신 커밋 값으로 조건을 평가한다. 동시에 들어온 중복 호출은
	 * 앞선 트랜잭션의 커밋을 기다린 뒤 COMPLETED 를 보고 0 행을 받으므로, 코스를 갱신하는 것은 1 행을 받은 쪽뿐이다.
	 * PENDING(발행 후 표시 전 릴레이 중단), FAILED(실패 처리 뒤 늦게 온 결과)도 완료로 받아들인다.
	 */
	public void completeAnalysis(UpdateBestSectionDto dto) {
		long locations = walkingDetailRepository.countLocations(dto.getCourseId()).orElse(0L);
		if (dto.getEndIdx() >= Math.max(locations, 1)) {
			throw new InvalidAnalysisResultException("endIdx " + dto.getEndIdx() + " >= locations " + locations);
		}
		if (outboxRepository.complete(dto.getCourseId(), LocalDateTime.now()) == 0) {
			if (!outboxRepository.existsByWalkingCourseId(dto.getCourseId())) {
				throw new NoWalkingCourseException();
			}
			log.info("[WalkingCommandService] analysis result ignored, already completed courseId={}",
				dto.getCourseId());
			return;
		}
		WalkingCourse course = walkingCourseRepository.findById(dto.getCourseId())
			.orElseThrow(() -> new NoWalkingCourseException());
		course.updateBestSection(dto.getMaxStress(), dto.getMinStress(), dto.getHealingStressAvg(), dto.getStartIdx(),
			dto.getEndIdx());
		log.info("[WalkingCommandService] analysis result applied courseId={}", dto.getCourseId());
	}
}