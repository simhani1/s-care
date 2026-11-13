package com.scare.api.core.template.response;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public enum ResponseCode {

	// 2000 - 성공
	OK("2000", "성공"),

	// 1000 - SECURITY
	UNAUTHENTICATED("1000", "인증되지 않은 사용자입니다."),
	EXPIRED_JWT_EXCEPTION("1001", "jwt 토큰이 만료되었습니다."),
	UNSUPPORTED_JWT_EXCEPTION("1002", "토큰 발급자가 일치하지 않습니다."),
	UNAUTHORIZED_EXCEPTION("1003", "토큰이 없거나 인증 과정에서 오류가 발생헀습니다."),

	// 3000 - MEMBER
	MEMBER_NOT_FOUND("3000", "회원이 존재하지 않습니다."),
	ALREADY_WITHDRAWN_MEMBER("3001", "이미 탈퇴된 회원입니다."),

	// 4000 - FAST
	FAIL_TO_GET_STRESS_DATE_FAST_API_SERVER("4000", "FAST API 에서 스트레스 데이터를 불러오지 못했습니다."),

	// 5000 - WALKING
	FAIL_TO_WALKING_COURSE("5000", "[ERROR] 산책 코스 서비스에서 예상치 못한 오류가 발생했습니다."),
	FAIL_TO_SAVE_WALKING_COURSE("5001", "[ERROR] 산책 코스 저장에 실패했습니다."),
	WALKING_COURSE_NOT_FOUND("5002", "산책 코스가 존재하지 않습니다."),

	// 6000 - Redis
	REDIS_TOKEN_STORED_EXCEPTION("6000", "Redis에서 Token관련 작업 중 오류가 발생했습니다.");

	private String code;
	private String message;

}