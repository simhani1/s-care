#!/bin/sh
# 로컬 스택을 띄우고 내린다. 사용: stack.sh up | down | status | logs
# 인프라는 docker compose, Spring 과 워커는 호스트 프로세스로 실행하고 로그와 pid 를 backend/.run 에 둔다.
set -eu
ROOT=$(git rev-parse --show-toplevel)
BACKEND="$ROOT/backend"
RUN="$BACKEND/.run"
mkdir -p "$RUN"

stop() {
  for name in spring worker; do
    if [ -f "$RUN/$name.pid" ]; then
      kill "$(cat "$RUN/$name.pid")" 2>/dev/null || true
      rm -f "$RUN/$name.pid"
    fi
  done
}

wait_http() {  # url, 이름
  i=0
  until curl -s -o /dev/null "$1"; do
    i=$((i + 1))
    if [ "$i" -gt 90 ]; then echo "$2 가 뜨지 않았다. 로그: $RUN/$2.log" >&2; tail -30 "$RUN/$2.log" >&2; exit 1; fi
    sleep 1
  done
}

case "${1:-}" in
  up)
    stop
    (cd "$BACKEND" && docker compose up -d --wait)
    if [ -x /usr/libexec/java_home ]; then JAVA_HOME=$(/usr/libexec/java_home -v 21); export JAVA_HOME; fi
    cd "$BACKEND/api"
    [ -f .env ] || cp .env.example .env
    sh gradlew build -x test -q
    nohup "${JAVA_HOME:+$JAVA_HOME/bin/}java" -Duser.timezone=Asia/Seoul -jar build/libs/api-0.0.1-SNAPSHOT.jar > "$RUN/spring.log" 2>&1 &
    echo $! > "$RUN/spring.pid"
    cd "$BACKEND/fast-api"
    # numpy<2 는 Python 3.12 까지만 휠이 있다
    if [ ! -x .venv/bin/python ]; then
      if command -v uv >/dev/null; then uv venv -q --python 3.12 --seed .venv
      else "$(command -v python3.12 || command -v python3)" -m venv .venv; fi
    fi
    .venv/bin/pip install -q -r requirements.txt
    # 워커의 print 출력이 버퍼에 갇히지 않게 한다
    PYTHONUNBUFFERED=1 nohup .venv/bin/uvicorn main:app --port 8000 > "$RUN/worker.log" 2>&1 &
    echo $! > "$RUN/worker.pid"
    wait_http http://localhost:8080/api-docs spring
    wait_http http://localhost:8000/docs worker
    echo "스택 준비 완료. 로그: $RUN"
    ;;
  down)
    stop
    (cd "$BACKEND" && docker compose down -v)
    ;;
  status)
    (cd "$BACKEND" && docker compose ps --format '{{.Service}} {{.Status}}')
    for name in spring worker; do
      if [ -f "$RUN/$name.pid" ] && kill -0 "$(cat "$RUN/$name.pid")" 2>/dev/null; then echo "$name 실행 중"; else echo "$name 중지"; fi
    done
    ;;
  logs)
    tail -n "${2:-40}" "$RUN/spring.log" "$RUN/worker.log"
    ;;
  *)
    echo "사용: stack.sh up | down | status | logs [줄 수]" >&2; exit 2
    ;;
esac
