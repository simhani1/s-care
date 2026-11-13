package com.scare.api.solution.walk.outbox;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface OutboxRepository extends JpaRepository<Outbox, Long> {

	@Query(value = "SELECT * FROM outbox WHERE outbox_id = :id AND status = 'PENDING' FOR UPDATE SKIP LOCKED",
		nativeQuery = true)
	Optional<Outbox> lockPending(@Param("id") Long id);

	@Query("SELECT o.id FROM Outbox o WHERE o.status = :status AND o.createdAt < :before ORDER BY o.id")
	List<Long> findIdsByStatusCreatedBefore(@Param("status") OutboxStatus status,
		@Param("before") LocalDateTime before, Pageable pageable);

	@Modifying
	@Query("UPDATE Outbox o SET o.status = :status, o.updatedAt = :now WHERE o.walkingCourseId = :courseId")
	int updateStatusByWalkingCourseId(@Param("courseId") Long courseId, @Param("status") OutboxStatus status,
		@Param("now") LocalDateTime now);

}
