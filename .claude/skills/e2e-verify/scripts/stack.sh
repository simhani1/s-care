#!/bin/sh
# 로컬 스택을 띄우고 내린다. 사용: stack.sh up | down | worker | status | logs
set -eu
ROOT=$(git rev-parse --show-toplevel)
BACKEND="$ROOT/backend"
RUN="$BACKEND/.run"
mkdir -p "$RUN"

stop() {
  for name in spring worker; do
    if [ -f "$RUN/$name.pid" ]; then
      pid=$(cat "$RUN/$name.pid")
      kill "$pid" 2>/dev/null || true
      i=0
      while kill -0 "$pid" 2>/dev/null && [ "$i" -lt 60 ]; do i=$((i + 1)); sleep 1; done
      rm -f "$RUN/$name.pid"
    fi
  done
}

wait_http() {
  i=0
  until curl -s -o /dev/null "$1"; do
    i=$((i + 1))
    if [ "$i" -gt 90 ]; then echo "$2 가 뜨지 않았다. 로그: $RUN/$2.log" >&2; tail -30 "$RUN/$2.log" >&2; exit 1; fi
    sleep 1
  done
}

start_worker() {
  if [ -f "$RUN/worker.pid" ]; then
    pid=$(cat "$RUN/worker.pid")
    kill "$pid" 2>/dev/null || true
    while kill -0 "$pid" 2>/dev/null; do sleep 0.2; done
  fi
  cd "$BACKEND/fast-api"
  secret=${INTERNAL_API_SECRET:-$(sed -n 's/^INTERNAL_API_SECRET=//p' "$BACKEND/api/.env")}
  SPRING_BASE_URL=${SPRING_BASE_URL:-http://localhost:8080} INTERNAL_API_SECRET=$secret PYTHONUNBUFFERED=1 \
    nohup .venv/bin/uvicorn main:app --port 8000 >> "$RUN/worker.log" 2>&1 &
  echo $! > "$RUN/worker.pid"
  wait_http http://localhost:8000/docs worker
}

case "${1:-}" in
  up)
    stop
    (cd "$BACKEND" && docker compose up -d --wait)
    if [ -x /usr/libexec/java_home ]; then JAVA_HOME=$(/usr/libexec/java_home -v 21); export JAVA_HOME; fi
    cd "$BACKEND/api"
    [ -f .env ] || cp .env.example .env
    sh gradlew build -x test -q
    OUTBOX_SWEEP_INTERVAL=${OUTBOX_SWEEP_INTERVAL:-PT5S} nohup "${JAVA_HOME:+$JAVA_HOME/bin/}java" -Duser.timezone=Asia/Seoul -jar build/libs/api-0.0.1-SNAPSHOT.jar > "$RUN/spring.log" 2>&1 &
    echo $! > "$RUN/spring.pid"
    cd "$BACKEND/fast-api"
    if [ ! -x .venv/bin/python ]; then
      if command -v uv >/dev/null; then uv venv -q --python 3.12 --seed .venv
      else "$(command -v python3.12 || command -v python3)" -m venv .venv; fi
    fi
    .venv/bin/pip install -q -r requirements.txt
    : > "$RUN/worker.log"
    start_worker
    wait_http http://localhost:8080/api-docs spring
    echo "스택 준비 완료. 로그: $RUN"
    ;;
  down)
    stop
    (cd "$BACKEND" && docker compose down -v)
    ;;
  worker)
    start_worker
    echo "워커 재기동. 로그: $RUN/worker.log"
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
    echo "사용: stack.sh up | down | worker | status | logs [줄 수]" >&2; exit 2
    ;;
esac
