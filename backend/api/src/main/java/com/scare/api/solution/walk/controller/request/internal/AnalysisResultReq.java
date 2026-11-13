package com.scare.api.solution.walk.controller.request.internal;

import java.util.Objects;

import com.scare.api.solution.walk.service.command.dto.UpdateBestSectionDto;

public record AnalysisResultReq(Integer maxStress, Integer minStress, Double healingStressAvg, Integer startIdx,
								Integer endIdx) {

	public AnalysisResultReq {
		Objects.requireNonNull(maxStress, "maxStress");
		Objects.requireNonNull(minStress, "minStress");
		Objects.requireNonNull(healingStressAvg, "healingStressAvg");
		Objects.requireNonNull(startIdx, "startIdx");
		Objects.requireNonNull(endIdx, "endIdx");
	}

	public UpdateBestSectionDto toDto(Long courseId) {
		return UpdateBestSectionDto.builder()
			.courseId(courseId)
			.maxStress(maxStress)
			.minStress(minStress)
			.healingStressAvg(healingStressAvg)
			.startIdx(startIdx)
			.endIdx(endIdx)
			.build();
	}
}
