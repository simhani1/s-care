package com.scare.api.solution.walk.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import com.scare.api.solution.walk.domain.WalkingDetail;

public interface WalkingDetailRepository extends JpaRepository<WalkingDetail, Long> {

	@Query(value = "SELECT JSON_LENGTH(location_data) FROM walking_detail WHERE walking_course_id = :id",
		nativeQuery = true)
	Optional<Long> countLocations(@Param("id") Long id);

}
