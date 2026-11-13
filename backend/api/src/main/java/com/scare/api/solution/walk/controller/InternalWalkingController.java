package com.scare.api.solution.walk.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.scare.api.core.template.response.BaseResponse;
import com.scare.api.core.template.response.ResponseCode;
import com.scare.api.solution.walk.controller.request.internal.AnalysisResultReq;
import com.scare.api.solution.walk.exception.InvalidAnalysisResultException;
import com.scare.api.solution.walk.exception.NoWalkingCourseException;
import com.scare.api.solution.walk.service.command.WalkingCommandService;

import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/v1/walking")
public class InternalWalkingController {

	private final WalkingCommandService walkingCommandService;

	@PutMapping("/{course-id}/analysis-result")
	public ResponseEntity<BaseResponse<?>> saveAnalysisResult(@PathVariable("course-id") Long courseId,
		@RequestBody AnalysisResultReq req) {
		walkingCommandService.completeAnalysis(req.toDto(courseId));
		return ResponseEntity.ok(BaseResponse.ofSuccess());
	}

	@ExceptionHandler(InvalidAnalysisResultException.class)
	public ResponseEntity<BaseResponse<?>> handleInvalidAnalysisResult() {
		return ResponseEntity.badRequest().body(BaseResponse.ofFail(ResponseCode.INVALID_ANALYSIS_RESULT));
	}

	@ExceptionHandler(NoWalkingCourseException.class)
	public ResponseEntity<BaseResponse<?>> handleNoWalkingCourse() {
		return ResponseEntity.status(HttpStatus.NOT_FOUND).body(BaseResponse.ofFail(ResponseCode.WALKING_COURSE_NOT_FOUND));
	}

}
