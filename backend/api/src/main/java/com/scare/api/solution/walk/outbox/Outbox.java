package com.scare.api.solution.walk.outbox;

import org.hibernate.annotations.DynamicUpdate;

import com.scare.api.core.domain.BaseTimeEntity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Table(name = "outbox", indexes = @Index(name = "idx_outbox_status", columnList = "status"))
@Getter
@DynamicUpdate
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
public class Outbox extends BaseTimeEntity {

	@Id
	@GeneratedValue(strategy = GenerationType.IDENTITY)
	@Column(name = "outbox_id")
	private Long id;

	@Column(name = "walking_course_id", nullable = false, unique = true)
	private Long walkingCourseId;

	@Column(name = "payload", nullable = false, columnDefinition = "json")
	private String payload;

	@Enumerated(EnumType.STRING)
	@Column(name = "status", nullable = false)
	private OutboxStatus status;

	@Builder
	public Outbox(Long walkingCourseId, String payload) {
		this.walkingCourseId = walkingCourseId;
		this.payload = payload;
		this.status = OutboxStatus.PENDING;
	}

	public void markPublished() {
		this.status = OutboxStatus.PUBLISHED;
	}

}
