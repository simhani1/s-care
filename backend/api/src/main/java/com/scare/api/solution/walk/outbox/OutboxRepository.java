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

	@Query("SELECT o.id FROM Outbox o WHERE o.status = :status ORDER BY o.id")
	List<Long> findIdsByStatus(@Param("status") OutboxStatus status, Pageable pageable);

	boolean existsByWalkingCourseId(Long walkingCourseId);

	@Modifying
	@Query("UPDATE Outbox o SET o.status = com.scare.api.solution.walk.outbox.OutboxStatus.COMPLETED, "
		+ "o.updatedAt = :now WHERE o.walkingCourseId = :courseId "
		+ "AND o.status <> com.scare.api.solution.walk.outbox.OutboxStatus.COMPLETED")
	int complete(@Param("courseId") Long courseId, @Param("now") LocalDateTime now);

	@Modifying
	@Query("UPDATE Outbox o SET o.status = com.scare.api.solution.walk.outbox.OutboxStatus.FAILED, "
		+ "o.updatedAt = :now WHERE o.status IN (com.scare.api.solution.walk.outbox.OutboxStatus.PENDING, "
		+ "com.scare.api.solution.walk.outbox.OutboxStatus.PUBLISHED) AND o.updatedAt < :threshold")
	int failStale(@Param("threshold") LocalDateTime threshold, @Param("now") LocalDateTime now);

}
