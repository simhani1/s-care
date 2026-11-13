package com.scare.api.solution.walk.domain;

import java.time.LocalDateTime;

import com.scare.api.core.domain.BaseTimeEntity;
import com.scare.api.member.domain.Member;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Table(name = "walking_course")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
public class WalkingCourse extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	@Column(name = "walking_course_id")
	private Long id;

	@Column(name = "min_stress", nullable = false)
	private double minStress;

	@Column(name = "max_stress", nullable = false)
	private double maxStress;

	@Column(name = "healing_stress_avg", nullable = false)
	private double healingStressAvg;

	@Column(name = "start_idx", nullable = false)
	private int startIdx;

	@Column(name = "end_idx", nullable = false)
	private int endIdx;

	@Column(name = "started_at", nullable = false)
	private LocalDateTime startedAt;

	@Column(name = "finished_at", nullable = false)
	private LocalDateTime finishedAt;

	@Enumerated(EnumType.STRING)
	@Column(name = "analysis_status", nullable = false)
	private AnalysisStatus analysisStatus;

	@ManyToOne(fetch = FetchType.LAZY)
	@JoinColumn(name = "member_id")
	private Member member;

	@Builder
	public WalkingCourse(double minStress, double maxStress, double healingStressAvg, int startIdx,
		int endIdx, LocalDateTime startedAt, LocalDateTime finishedAt, Member member) {
		this.minStress = minStress;
		this.maxStress = maxStress;
		this.healingStressAvg = healingStressAvg;
		this.startIdx = startIdx;
		this.endIdx = endIdx;
		this.startedAt = startedAt;
		this.finishedAt = finishedAt;
		this.member = member;
		this.analysisStatus = AnalysisStatus.ANALYZING;
	}

	public boolean hasHealingSection() {
		return this.healingStressAvg != 0.0;
	}

	public void updateBestSection(int maxStress, int minStress, Double healingStressAvg, Integer startIdx,
		Integer endIdx) {
		this.maxStress = maxStress;
		this.minStress = minStress;
		this.healingStressAvg = healingStressAvg;
		this.startIdx = startIdx;
		this.endIdx = endIdx;
		this.analysisStatus = AnalysisStatus.COMPLETED;
	}

}
