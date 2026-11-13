package com.scare.api.solution.walk.repository;

import org.springframework.data.jpa.repository.JpaRepository;

import com.scare.api.solution.walk.domain.WalkingDetail;

public interface WalkingDetailRepository extends JpaRepository<WalkingDetail, Long> {
}
