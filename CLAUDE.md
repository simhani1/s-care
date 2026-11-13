# S-Care

스트레스 관리 서비스. 안드로이드 앱(`android/`), Spring API(`backend/api`), 스트레스 계산 워커(`backend/fast-api`).

## 실행과 빌드

- 인프라: `cd backend && docker compose up -d --wait`
- Spring (JDK 21): `cd backend/api && cp .env.example .env && sh gradlew bootRun`. 빌드는 `sh gradlew build -x test`. `gradlew` 에 실행 권한이 없어 `sh` 로 부른다.
- 워커 (Python 3.12): `cd backend/fast-api && .venv/bin/uvicorn main:app --port 8000`
- 자세한 내용은 `backend/README.md`.

## Git

- 이 저장소는 `S-Care/s-care` 의 포크다. PR 은 반드시 `--repo simhani1/s-care --base main` 으로 올린다. 생략하면 원본 저장소로 올라간다.
- 운영 접속 정보를 커밋하지 않는다. `.env` 는 무시되고 `.env.example` 에는 로컬 전용 값만 둔다.

## 하네스: 산책 저장 흐름 고도화

**목표:** `docs/spec/walk-save-improvement.md` 스펙을 PR 단위로 구현하고 독립 검증을 거쳐 main 에 병합한다.

**트리거:** 산책 저장 흐름, 아웃박스, 스트레스 계산, 스펙의 PR 진행과 관련된 작업 요청 시 `walk-save-pr` 스킬을 사용하라. 단순 질문은 직접 응답 가능.

**변경 이력:**
| 날짜 | 변경 내용 | 대상 | 사유 |
|------|----------|------|------|
| 2026-11-13 | 초기 구성 | 전체 | - |
| 2026-11-13 | 워커 로그 버퍼링 해제 | skills/e2e-verify/scripts/stack.sh | PR 2 검증에서 워커 출력이 로그에 남지 않음 |
