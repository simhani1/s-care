---
name: e2e-verify
description: "S-Care 백엔드를 로컬에서 실제로 띄워 종단 간으로 검증한다. docker compose 인프라, Spring API, FastAPI 워커를 기동하고 산책 저장부터 결과 조회까지 시나리오를 실행한다. 산책 저장 흐름, 아웃박스, 큐, 스트레스 계산을 바꾼 뒤 '동작 확인', '검증', '스모크 테스트', '종단 간 테스트', '로컬에서 돌려봐', '다시 검증' 요청이 있으면 반드시 이 스킬을 사용할 것. 단위 테스트만 돌리는 요청에는 쓰지 않는다."
---

# 종단 간 검증

빌드와 단위 테스트가 통과해도 Spring, RabbitMQ, FastAPI, MySQL 이 맞물리는지는 알 수 없다. 이 스킬은 실제로 띄워서 확인한다.

## 절차

1. 스택을 띄운다. 현재 작업 트리의 코드로 빌드하므로, 검증할 브랜치에서 실행한다.

   ```bash
   .claude/skills/e2e-verify/scripts/stack.sh up
   ```

   Docker 데몬이 꺼져 있으면 먼저 켠다. 8080, 8000, 3306, 5672 포트가 필요하다.

2. 시나리오를 실행한다.

   ```bash
   python3 .claude/skills/e2e-verify/scripts/smoke.py basic 600
   ```

   두 번째 인자는 심박 샘플 수다. 초당 1개라 600 은 10분 산책이다. 힐링 구간은 최소 산책 시간 이상에서만 나온다.

3. 실패 경로를 직접 만든다. 변경한 부분에 맞는 것을 고른다.

   | 확인할 것 | 방법 |
   |---|---|
   | 워커가 죽어 있을 때 | `kill $(cat backend/.run/worker.pid)` 후 저장하고, 워커를 다시 띄워 결과가 반영되는지 본다 |
   | Spring 이 잠시 죽었을 때 | 워커가 재시도하는지 `stack.sh logs` 로 본다 |
   | 중복 전달 | RabbitMQ 관리 콘솔(http://localhost:15672, scare / scare)에서 같은 메시지를 다시 넣는다 |
   | 큐 상태 | `cd backend && docker compose exec rabbitmq rabbitmqctl list_queues name messages messages_unacknowledged` |
   | DB 상태 | `cd backend && docker compose exec mysql mysql -uscare -pscare scare -e "<쿼리>"` |

4. 로그에서 예외를 확인한다. 시나리오가 통과해도 삼켜진 예외가 있을 수 있다.

   ```bash
   grep -nE "ERROR|Exception|Traceback" backend/.run/spring.log backend/.run/worker.log
   ```

   Spring 기동 직후의 `Table ... doesn't exist` 는 `ddl-auto: create-drop` 이 빈 DB 에서 내는 것이라 무시한다.

5. 끝나면 `stack.sh down` 으로 내린다. 볼륨까지 지우므로 다음 실행은 빈 DB 에서 시작한다.

## 시나리오를 추가할 때

`smoke.py` 의 `SCENARIOS` 에 함수를 추가한다. 새 요구사항이 생기면 그 요구사항이 깨졌을 때 실패하는 시나리오를 같은 PR 에 넣는다. 상태를 기다릴 때는 `wait_for` 를 쓴다. 고정 시간 대기는 느린 환경에서 깨진다.

## 보고

실행한 명령과 실제 출력을 그대로 남긴다. 돌리지 못한 시나리오는 통과로 적지 않는다.
