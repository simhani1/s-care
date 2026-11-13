package com.scare.api.solution.walk.service.query.dto;

import java.util.List;
import java.util.stream.Collectors;

import com.scare.api.core.util.DateConverter;
import com.scare.api.solution.walk.domain.AnalysisStatus;
import com.scare.api.solution.walk.domain.WalkingCourse;
import com.scare.api.solution.walk.domain.WalkingDetail;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
@AllArgsConstructor
public class WalkingCourseDto {

	private Long courseId;
	private Long startedAt;
	private Long finishedAt;
	private List<Pos> posList;
	private Integer startIdx;
	private Integer endIdx;
	private double maxStress;
	private double minStress;
	private AnalysisStatus analysisStatus;

	public static WalkingCourseDto from(WalkingCourse walkingCourse, WalkingDetail walkingDetail) {
		return WalkingCourseDto.builder()
			.courseId(walkingCourse.getId())
			.startedAt(DateConverter.convertToLong(walkingCourse.getStartedAt()))
			.finishedAt(DateConverter.convertToLong(walkingCourse.getFinishedAt()))
			.startIdx(walkingCourse.getStartIdx())
			.endIdx(walkingCourse.getEndIdx())
			.maxStress(walkingCourse.getMaxStress())
			.minStress(walkingCourse.getMinStress())
			.analysisStatus(walkingCourse.getAnalysisStatus())
			.posList(
				walkingDetail.getLocationData().stream()
					.map(locationData -> Pos.builder()
						.lat(locationData.getLatitude())
						.lng(locationData.getLongitude())
						.build())
					.collect(Collectors.toList())
			)
			.build();
	}

	public static WalkingCourseDto from(WalkingCourse walkingCourse) {
		return WalkingCourseDto.builder()
			.courseId(walkingCourse.getId())
			.startedAt(DateConverter.convertToLong(walkingCourse.getStartedAt()))
			.finishedAt(DateConverter.convertToLong(walkingCourse.getFinishedAt()))
			.startIdx(walkingCourse.getStartIdx())
			.endIdx(walkingCourse.getEndIdx())
			.maxStress(walkingCourse.getMaxStress())
			.minStress(walkingCourse.getMinStress())
			.analysisStatus(walkingCourse.getAnalysisStatus())
			.build();
	}

}
