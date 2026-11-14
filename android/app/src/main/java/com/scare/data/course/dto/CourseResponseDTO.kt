package com.scare.data.course.dto

data class CourseListAPIResponseDTO(
    val code: String,
    val message: String,
    val data: List<CourseResponseDTO>,
    val isSuccess: Boolean
)

data class CourseDetailAPIResponseDTO(
    val code: String,
    val message: String,
    val data: CourseResponseDTO,
    val isSuccess: Boolean
)

data class CourseResponseDTO(
    val courseId: Long,
    val startedAt: Long,
    val finishedAt: Long,
    val posList: List<PositionDTO>?,
    val startIdx: Int,
    val endIdx: Int,
    val maxStress: Double,
    val minStress: Double,
    val distance: Double,
    val analysisStatus: String? = null
)