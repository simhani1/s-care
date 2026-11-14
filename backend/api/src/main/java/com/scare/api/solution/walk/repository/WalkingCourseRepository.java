package com.scare.api.solution.walk.repository;

import java.time.LocalDateTime;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.scare.api.member.domain.Member;
import com.scare.api.solution.walk.domain.WalkingCourse;

public interface WalkingCourseRepository extends JpaRepository<WalkingCourse, Long> {

	Page<WalkingCourse> findAllByMemberOrderByCreatedAtDesc(Member member, PageRequest of);

	@Modifying
	@Query("UPDATE WalkingCourse c SET c.analysisStatus = com.scare.api.solution.walk.domain.AnalysisStatus.FAILED, "
		+ "c.updatedAt = :now WHERE c.id = :id "
		+ "AND c.analysisStatus = com.scare.api.solution.walk.domain.AnalysisStatus.ANALYZING")
	int failAnalyzing(@Param("id") Long id, @Param("now") LocalDateTime now);

}
