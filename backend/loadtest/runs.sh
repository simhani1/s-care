#!/bin/sh
# RESULTS.md 의 측정 전부. bench/sync-baseline 에서 스택을 띄운 뒤 실행한다. 사용: runs.sh <phase>...
# 예산: 0.12 = 2024 서버(크레딧 소진 가정), 0.28 = 같은 서버 비소진 가정. 근거는 RESULTS.md 보정 절.
set -eu
B="python3 $(dirname "$0")/bench.py"
T=0.12
U=0.28

for phase in "$@"; do
  case $phase in
    single)   # 길이별 단건
      for c in $T $U; do for a in prefix window; do for arch in sync queue; do
        $B single --arch $arch --cpus $c --algo $a --minutes 10,20,30,60; done; done; done ;;
    why22)    # 22초가 60초 제한 뒤에서 실패한 이유: 길이(35, 37분)와 동시 요청(22분 산책 k건)
      $B single --arch sync --cpus $T --algo prefix --minutes 35,37,40
      for n in 1 2 3; do $B burst --arch sync --cpus $T --algo prefix --minutes 22 --n $n; done ;;
    poll)     # 단건 저장부터 결과까지의 분포(폴링 간격 근거), 30분 산책 10회
      for c in $T $U; do for a in window prefix; do
        $B single --arch queue --cpus $c --algo $a --minutes 30,30,30,30,30,30,30,30,30,30 --label poll; done; done ;;
    burst)    # 동시에 산책을 마친 N명. 큐 대기 모델(마지막 결과 = 릴레이 + ceil(N/k) x 1건 시간) 검증과 동기 대비
      $B burst --arch queue --cpus $T --algo window --minutes 30 --n 10
      $B burst --arch queue --cpus $T --algo window --minutes 30 --n 40 --workers 4
      $B burst --arch queue --cpus $T --algo window --minutes 10 --n 30
      $B burst --arch queue --cpus $T --algo prefix --minutes 30 --n 3
      $B burst --arch queue --cpus $T --algo prefix --minutes 30 --n 12 --workers 4
      $B burst --arch queue --cpus $T --algo prefix --minutes 10 --n 10
      $B burst --arch queue --cpus $U --algo window --minutes 30 --n 30
      $B burst --arch queue --cpus $U --algo window --minutes 30 --n 100 --workers 4
      $B burst --arch queue --cpus $U --algo prefix --minutes 30 --n 10
      $B burst --arch queue --cpus $U --algo prefix --minutes 30 --n 40 --workers 4
      $B burst --arch queue --cpus $U --algo prefix --minutes 60 --n 5 --workers 2
      for n in 3 10 30; do
        $B burst --arch sync --cpus $T --algo prefix --minutes 30 --n $n
        $B burst --arch sync --cpus $T --algo window --minutes 30 --n $n
        $B burst --arch sync --cpus $U --algo prefix --minutes 30 --n $n
        $B burst --arch sync --cpus $U --algo window --minutes 30 --n $n
      done ;;
    ramp)     # 30분 산책 유입량 0.5, 1, 2, 5배(1배 = 워커 1대 처리량), 각 120초
      for r in 0.05 0.1 0.2 0.5; do for arch in sync queue; do $B rate --arch $arch --cpus $T --algo window --rate $r; done
        $B rate --arch sync --cpus $T --algo prefix --rate $r; done
      for r in 0.25 0.5 1 2.5; do for arch in sync queue; do $B rate --arch $arch --cpus $U --algo window --rate $r; done; done ;;
    fault)    # 계산기 무응답(pause), 중지(stop): 30초 정상, 90초 장애, 이후 복구. 초당 0.3건
      for m in pause stop; do for arch in sync queue; do $B fault --arch $arch --cpus $U --algo window --mode $m --rate 0.3; done; done ;;
    scale)    # 계산기 k대에 k대 처리량의 1.5배 유입, 90초
      for k in 1 2 4; do r=$(python3 -c "print(round(0.15 * $k, 2))")
        for arch in sync queue; do $B rate --arch $arch --cpus $T --algo window --rate "$r" --seconds 90 --workers $k; done; done ;;
    *) echo "unknown phase $phase" >&2; exit 2 ;;
  esac
done
