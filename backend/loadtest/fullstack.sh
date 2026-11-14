#!/bin/sh
# 박스 전체 예산 변형: 계산기뿐 아니라 Spring, MySQL, RabbitMQ 도 CPU 를 제한해 합이 t2.xlarge 예산이 되게 한다.
# 사용: fullstack.sh <depleted|credits> [burst]. stack.sh up 으로 띄운 상태에서 실행하면 호스트 Spring 을 내리고 컨테이너 Spring 을 띄운다.
# 끝나면 제한을 풀고 컨테이너 Spring 을 내린다. 호스트 Spring 은 stack.sh up 으로 다시 띄운다.
set -eu
ROOT=$(git rev-parse --show-toplevel)
B="python3 $ROOT/backend/loadtest/bench.py"
C="docker compose -f docker-compose.yml -f loadtest/compose.bench.yml --profile fullstack"
cd "$ROOT/backend"

case ${1:-} in
  depleted) calc=0.12 api=0.2 mysql=0.1 mq=0.06 ;;   # 합 0.48 = 0.12 x 4 vCPU
  credits)  calc=0.28 api=0.5 mysql=0.2 mq=0.14 ;;   # 합 1.12 = 0.28 x 4 vCPU
  *) echo "사용: fullstack.sh depleted|credits" >&2; exit 2 ;;
esac

if [ -f .run/spring.pid ]; then kill "$(cat .run/spring.pid)" 2>/dev/null || true; rm -f .run/spring.pid; sleep 5; fi
docker update --cpus "$mysql" scare-mysql-1 >/dev/null
docker update --cpus "$mq" scare-rabbitmq-1 >/dev/null
API_CPUS=$api $C up -d --no-deps --force-recreate api
started=$(date +%s)
until curl -s -o /dev/null http://localhost:8080/api-docs; do sleep 2; done
echo "api up in $(( $(date +%s) - started ))s at cpus=$api"

trap 'docker update --cpus "$(docker info --format '{{.NCPU}}')" scare-mysql-1 scare-rabbitmq-1 >/dev/null; $C rm -sf api >/dev/null 2>&1' EXIT
L="--label fullstack-$1"
# 기동 직후 첫 부하는 JIT 이전이라 저장이 느리다. 60초 저부하로 데운 뒤 잰다.
$B rate --arch queue --cpus $calc --algo window --rate 0.2 --seconds 60 --label warmup
if [ "${2:-}" = burst ]; then
  n=$([ "$1" = depleted ] && echo 10 || echo 30)
  for arch in queue sync; do $B burst --arch $arch --cpus $calc --algo window --minutes 30 --n $n --label "fullstack-$1-warm"; done
elif [ "$1" = depleted ]; then
  for arch in queue sync; do
    $B burst --arch $arch --cpus $calc --algo window --minutes 30 --n 10 $L
    $B burst --arch $arch --cpus $calc --algo prefix --minutes 30 --n 3 $L
    for r in 0.05 0.1 0.2; do $B rate --arch $arch --cpus $calc --algo window --rate $r $L; done
  done
else
  for arch in queue sync; do
    $B burst --arch $arch --cpus $calc --algo window --minutes 30 --n 30 $L
    $B burst --arch $arch --cpus $calc --algo prefix --minutes 30 --n 10 $L
    for r in 0.25 0.5 1; do $B rate --arch $arch --cpus $calc --algo window --rate $r $L; done
  done
fi
