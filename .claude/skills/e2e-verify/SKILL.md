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

   Docker 데몬이 꺼져 있으면 먼저 켠다. 8080, 8000, 3306, 5672, 15672 포트가 필요하다.

   `backend/api/.env` 는 없을 때만 `.env.example` 에서 복사된다. 예시에 키가 추가되면(PR 5 의 `INTERNAL_API_SECRET`) 직접 옮긴다. PR 5 이전 브로커가 떠 있으면 `request_queue` 인수가 달라 선언이 거부되므로 `stack.sh down` 후 띄운다. Spring 은 실패 처리 주기 `OUTBOX_SWEEP_INTERVAL=PT5S` 로 뜬다(운영 기본 1시간). 릴레이 주기는 10초다. 워커는 `SPRING_BASE_URL`, `INTERNAL_API_SECRET`(`backend/api/.env` 의 값)을 받아 뜬다. `stack.sh worker` 는 워커만 다시 띄우고, `INTERNAL_API_SECRET=... stack.sh worker` 로 비밀을 바꿔 띄울 수 있다.

2. 시나리오를 실행한다.

   ```bash
   python3 .claude/skills/e2e-verify/scripts/smoke.py basic 600
   ```

   두 번째 인자는 심박 샘플 수다. 초당 1개라 600 은 10분 산책이다. 힐링 구간은 최소 산책 시간 이상에서만 나온다.

   | 시나리오 | 확인하는 것 |
   |---|---|
   | `basic` | 저장 직후 상태가 `ANALYZING` 또는 `COMPLETED`, 이후 상세와 목록의 `analysisStatus` 와 아웃박스가 `COMPLETED` |
   | `outbox` | 워커를 `SIGSTOP` 으로 멈춘 채 저장해 아웃박스가 `PUBLISHED` 로 머물고, 스케줄러가 한 번 더 도는 12초 뒤에도 큐 메시지가 1개뿐인지 본다. 재개 후 `COMPLETED`. 약 25초 걸린다 |
   | `broker-outage` | `docker compose stop rabbitmq` 상태에서 저장이 2초 안에 200 이고 코스는 `ANALYZING`, 아웃박스는 `PENDING`. 브로커를 다시 켜면 스케줄러가 발행해 `COMPLETED` 가 된다. 실패해도 브로커는 다시 켠다 |
   | `concurrent` | 저장 30건을 동시에 보내 모두 200 이고 가장 느린 응답이 3초 미만인지, 30건 모두 `COMPLETED` 가 되는지 본다. 저장 경로가 브로커나 두 번째 DB 커넥션을 기다리는 회귀(풀 교착)를 잡는다 |
   | `broker-hang` | `docker compose pause rabbitmq` 상태에서 저장 4건(사이에 12초 대기)이 각각 1초 안에 200 이고 `ANALYZING` 인지 본다. `unpause` 후 모두 `COMPLETED`. 실패해도 브로커는 다시 재개한다. 약 25초 걸린다 |
   | `spring-pause` | 워커를 멈춘 채 발행시킨 뒤 Spring 을 `SIGSTOP` 하고 워커를 재개한다. 워커 로그에 재시도가 찍히는 동안 메시지가 미확인(unacked 1)이고 코스가 `ANALYZING` 인지 본다. Spring 재개 후 `COMPLETED`, 마지막 PUT 만 200 이고 그 뒤에 `acked`, 큐가 비는지 본다 |
   | `duplicate` | 워커를 멈춘 채 발행시킨 뒤 내부 저장 API 를 동시 10건, 다른 값으로 1건 더 호출해 모두 200 이고 spring.log 의 `analysis result applied` 가 1번인지 본다. 워커 재개 후 워커 결과도 200 으로 ack 되고 코스 값은 처음 반영한 값 그대로다 |
   | `auth` | 비밀 없음, 틀린 비밀, 사용자 JWT, JWT + 틀린 비밀이 모두 403, 없는 코스 404, 빈 본문 400, 값 검증(min > max, 60 초과, 음수 평균, `"NaN"`, start > end, 좌표 수 이상) 400, 모르는 필드 200, 거부된 호출이 코스를 바꾸지 않는지 본다 |
   | `poison` | 심박 3개, 0 bpm 산책이 데드레터 큐(`request_queue.dlq`)로 가고 뒤에 저장한 정상 산책은 `COMPLETED`, 실패한 코스는 `ANALYZING` 으로 남는지 본다. 관리 API 로 데드레터 메시지의 `delivery_mode` 2 와 `x-death` 를 확인한다 |
   | `sweep` | PUBLISHED 행의 `updated_at` 을 2시간 앞으로 옮겨 아웃박스와 코스가 `FAILED` 가 되고, 워커를 재개하면 늦은 결과로 `COMPLETED` 가 되는지 본다. 브로커를 멈춘 채 저장한 PENDING 행은 같은 방법으로 앞당겨도 12초 뒤 그대로 `PENDING` 이고, 브로커 복구 후 릴레이가 발행해 `COMPLETED` 가 되는지 본다. 약 40초 걸린다 |
   | `wrong-secret` | `INTERNAL_API_SECRET=wrong-secret stack.sh worker` 로 띄운 워커가 403 을 한 번 받고 종료하는지, 메시지가 `request_queue` 에 그대로(ready 1, unacked 0) 남고 데드레터 큐가 늘지 않는지 본다. 맞는 비밀로 `stack.sh worker` 후 `COMPLETED` |
   | `sweep-race` | 코스 없는 FAILED 행 5000개를 넣고, 워커를 멈춘 채 PUBLISHED 30행을 만든 뒤 저장 3스레드를 20초 동안 보내면서 그 행들을 차례로 2시간 앞당긴다. 실패 처리가 도는 동안 저장이 모두 200 인지(교착 회귀), 앞당긴 30행이 워커 재개 후 `COMPLETED` 인지 본다. 부하용 산책은 끝에 아웃박스를 `FAILED` 로 바꾸고 큐를 비운다. 약 30초 걸린다 |

   전체를 한 번에: `for s in basic outbox broker-outage concurrent broker-hang spring-pause duplicate auth poison sweep wrong-secret sweep-race; do python3 .claude/skills/e2e-verify/scripts/smoke.py $s 600 || break; done`. `basic` 과 `auth` 외의 시나리오는 docker compose 와 `backend/.run/*.pid` 를 직접 다룬다.

   브로커 장애 중 릴레이 한 번이 트랜잭션을 쥔 시간은 spring.log 의 `publish failed after {ms}ms` 에 남는다.

   저장 트랜잭션의 경계를 보려면 `LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_ORM_JPA=DEBUG stack.sh up` 으로 띄운다. 로그 이름은 대소문자를 구분하므로 클래스 이름까지 넣으면 적용되지 않는다.

3. 실패 경로를 직접 만든다. 변경한 부분에 맞는 것을 고른다.

   | 확인할 것 | 방법 |
   |---|---|
   | 워커가 죽어 있을 때 | `kill $(cat backend/.run/worker.pid)` 후 저장하고, 워커를 다시 띄워 결과가 반영되는지 본다 |
   | Spring 이 잠시 죽었을 때 | `spring-pause` 시나리오. `kill` 은 `create-drop` 이 테이블을 지우므로 쓰지 않는다. 연결 거부 경로는 `backend/fast-api/tests/test_delivery.py` 가 다룬다 |
   | 중복 전달 | RabbitMQ 관리 콘솔(http://localhost:15672, scare / scare)에서 같은 메시지를 다시 넣는다 |
   | 큐 상태 | `cd backend && docker compose exec rabbitmq rabbitmqctl list_queues name messages messages_unacknowledged arguments` |
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
