package com.scare.api.solution.walk.domain;

import java.time.LocalDateTime;
import lombok.Builder;
import lombok.Getter;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;

import java.util.List;

@Document(collection = "walking_detail")
@Getter
public class WalkingDetail {

    @Id
    @Field("walking_history_id")
    private Long id;

    @Field("location_data")
    private List<LocationPoint> locationData;

    @Builder
    public WalkingDetail(Long id, List<LocationPoint> locationData) {
        this.id = id;
        this.locationData = locationData;
    }

    @Getter
    public static class LocationPoint {
        private double latitude;
        private double longitude;
        private double stressIndex;
        private LocalDateTime createdAt;

        @Builder
        public LocationPoint(double latitude, double longitude, double stressIndex, LocalDateTime createdAt) {
            this.latitude = latitude;
            this.longitude = longitude;
            this.stressIndex = stressIndex;
            this.createdAt = createdAt;
        }
    }
}