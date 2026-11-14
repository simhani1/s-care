"""큐 구조 수용량 표. 1건 계산 시간 T(보정 측정값)로 FIFO 대기 모델을 계산한다.
동시에 N명이 저장하면 마지막 결과 = 릴레이 대기(최대 10초) + 0.5초 + ceil(N/k) x T. 같은 조건의 burst 측정과 RESULTS.md 에서 대조한다.
사용: python3 capacity.py"""
import math

# 컨테이너 1개, --cpus 고정에서 잰 1건 계산 시간 중앙값(초). calibrate.py 결과
T = {
    ("depleted", "prefix"): {10: 4.85, 20: 16.5, 30: 35.1, 60: 136.3},
    ("depleted", "window"): {10: 2.5, 20: 6.6, 30: 9.5, 60: 17.9},
    ("credits", "prefix"): {10: 1.0, 20: 3.65, 30: 8.0, 60: 29.7},
    ("credits", "window"): {10: 0.61, 20: 1.30, 30: 1.82, 60: 4.21},
}
RELAY = 10.5


def last_result(n, k, t):
    return RELAY + math.ceil(n / k) * t


def max_users(limit, k, t):
    return max(0, k * math.floor((limit - RELAY) / t))


assert last_result(10, 1, 9.5) == 105.5 and max_users(60, 1, 9.5) == 5 and max_users(60, 4, 136.3) == 0

if __name__ == "__main__":
    print("| 예산 | 계산 | 산책 | 1건 계산 | 워커 1대 시간당 | 1분 안에 (k=1/2/4) | 3분 안에 | 5분 안에 |")
    print("|---|---|---|---|---|---|---|---|")
    for (budget, algo), ts in T.items():
        for m, t in ts.items():
            cells = ["/".join(str(max_users(lim, k, t)) for k in (1, 2, 4)) for lim in (60, 180, 300)]
            print(f"| {budget} | {algo} | {m}분 | {t:.1f}초 | {3600 / t:.0f}건 | " + " | ".join(cells) + " |")
