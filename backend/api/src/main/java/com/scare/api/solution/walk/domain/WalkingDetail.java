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
