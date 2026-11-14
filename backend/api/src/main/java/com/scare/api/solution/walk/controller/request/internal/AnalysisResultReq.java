package com.scare.api.solution.walk.controller.request.internal;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.scare.api.solution.walk.service.command.dto.UpdateBestSectionDto;

@JsonIgnoreProperties(ignoreUnknown = true)
public record AnalysisResultReq(Double maxStress, Double minStress, Double healingStressAvg, Integer startIdx,
								Integer endIdx) {

	public static final double MAX_STRESS = 60;

	public AnalysisResultReq {
		require(isScore(maxStress) && isScore(minStress) && minStress <= maxStress, "maxStress/minStress");
		require(isScore(healingStressAvg), "healingStressAvg");
		require(startIdx != null && endIdx != null && 0 <= startIdx && startIdx <= endIdx, "startIdx/endIdx");
	}

	private static boolean isScore(Double value) {
		return value != null && Double.isFinite(value) && 0 <= value && value <= MAX_STRESS;
	}

	private static void require(boolean valid, String field) {
		if (!valid) {
			throw new IllegalArgumentException("invalid analysis result: " + field);
		}
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
