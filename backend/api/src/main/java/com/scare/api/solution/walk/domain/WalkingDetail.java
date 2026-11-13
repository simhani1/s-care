package com.scare.api.solution.walk.domain;

import java.util.List;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;

// 좌표는 목록 조회가 읽지 않도록 walking_course 와 분리한다. PK 는 코스 ID 를 그대로 쓴다(1:1).
@Table(name = "walking_detail")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Entity
public class WalkingDetail {

	@Id
	@Column(name = "walking_course_id")
	private Long id;

	@JdbcTypeCode(SqlTypes.JSON)
	@Column(name = "location_data", nullable = false)
	private List<LocationPoint> locationData;

	@Builder
	public WalkingDetail(Long id, List<LocationPoint> locationData) {
		this.id = id;
		this.locationData = locationData;
	}

	// 값 비교가 없으면 Hibernate 가 JSON 을 매번 변경된 것으로 보고 INSERT 뒤에 같은 값으로 UPDATE 한다
	@EqualsAndHashCode
	@Getter
	@NoArgsConstructor(access = AccessLevel.PROTECTED)
	public static class LocationPoint {
		private double latitude;
		private double longitude;

		@Builder
		public LocationPoint(double latitude, double longitude) {
			this.latitude = latitude;
			this.longitude = longitude;
		}
	}
}
