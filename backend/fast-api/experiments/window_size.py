"""윈도우 크기 실험.

회복(힐링) 구간의 위치를 알고 있는 합성 산책을 만들고, 윈도우 크기별로
알고리즘이 그 구간을 얼마나 정확히 찾는지 잰다.

실행: python -m experiments.window_size [조건당 반복 횟수]   (backend/fast-api 에서)

지표
- 겹침: 고른 구간과 실제 회복 구간이 겹친 길이 / 둘 중 짧은 구간의 길이
- IoU: 고른 구간과 실제 구간의 겹침 / 합침
- 적중률: 겹침 >= 0.8 인 산책의 비율
- 점수 흔들림: 상태가 변하지 않는 산책에서 스트레스 점수가 스스로 출렁이는 정도
"""
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from experiments.synthetic import make_walk
from services.calculate_service import get_single_stress, get_windowed_stress_index
from services.stress_overview_service import find_healing_course_idx, locate_healing_section

warnings.filterwarnings("ignore")

WINDOWS = [20, 30, 45, 60, 90, 120, 180, 240, 300]
CONTRASTS = {"아주 약함": 0.15, "약함": 0.2, "중간": 0.3, "강함": 0.5}
SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
PREFIX = "누적(기존)"


def overlap(found, truth):
    """(정규화 겹침, IoU). 정규화 겹침은 겹친 길이를 두 구간 중 짧은 쪽 길이로 나눈 값이다.
    고르는 구간 길이(전체의 1/3)와 실제 회복 구간 길이가 달라서 생기는 손해를 빼고 위치만 본다."""
    fs, fe = found
    ts, te = truth
    inter = max(0, min(fe, te) - max(fs, ts))
    return inter / max(1, min(fe - fs, te - ts)), inter / max(1, max(fe, te) - min(fs, ts))


def locate(hr, window):
    stress = get_windowed_stress_index(hr, window)
    _, s, e = locate_healing_section(stress, min(window, len(hr)))
    return s, e + 1


def locate_prefix(hr):
    stress = [get_single_stress(hr[:i]) for i in range(4, len(hr) + 1)]
    _, s, e = find_healing_course_idx(stress)
    return s + 3, e + 3 + 1


def one_walk(args):
    n, base_tension, seed, windows, with_prefix = args
    rng = np.random.default_rng(seed)
    length = int(rng.uniform(n / 5, n / 2))
    start = int(rng.uniform(0, n - length))
    truth = (start, start + length)
    hr = make_walk(n, truth, rng, base_tension=base_tension)
    out = {}
    for w in windows:
        t0 = time.perf_counter()
        found = locate(hr, w)
        out[w] = (*overlap(found, truth), time.perf_counter() - t0)
    if with_prefix:
        t0 = time.perf_counter()
        out[PREFIX] = (*overlap(locate_prefix(hr), truth), time.perf_counter() - t0)
    return out


def run(n, base_tension, windows, with_prefix, pool):
    jobs = [(n, base_tension, seed, windows, with_prefix) for seed in range(SEEDS)]
    results = list(pool.map(one_walk, jobs))
    keys = list(windows) + ([PREFIX] if with_prefix else [])
    return {k: np.array([r[k] for r in results]) for k in keys}


def row(label, arr):
    hit, iou, sec = arr[:, 0], arr[:, 1], arr[:, 2]
    return f"| {label} | {hit.mean():.2f} | {iou.mean():.2f} | {(hit >= 0.8).mean() * 100:3.0f}% | {sec.mean() * 1000:5.0f}ms |"


def stationary(args):
    tension, seed = args
    hr = make_walk(600, None, np.random.default_rng(1000 + seed), base_tension=tension)
    out = {}
    for w in WINDOWS:
        s = np.array(get_windowed_stress_index(hr, w))
        out[w] = (s.mean(), s.std(), s.max() - s.min())
    return out


def main():
    with ProcessPoolExecutor() as pool:
        print(f"## 1. 점수 흔들림 (상태가 일정한 10분 산책, 조건당 {SEEDS}회)\n")
        print("실제 변화는 0 이므로 표준편차와 최대-최소 차이는 작을수록 좋다.\n")
        tensions = [0.1, 0.3, 0.5]
        print("| 윈도우 | " + " | ".join(f"tension {t}: 평균 / 표준편차 / 최대-최소" for t in tensions) + " |\n|---|" + "---|" * len(tensions))
        stat = {t: list(pool.map(stationary, [(t, seed) for seed in range(SEEDS)])) for t in tensions}
        for w in WINDOWS:
            cells = []
            for t in tensions:
                a = np.array([r[w] for r in stat[t]]).mean(axis=0)
                cells.append(f"{a[0]:4.1f} / {a[1]:3.1f} / {a[2]:4.1f}")
            print(f"| {w} | " + " | ".join(cells) + " |")
        print()
        sys.stdout.flush()

        print(f"## 2. 윈도우 크기별 회복 구간 탐지 (20분 산책, 조건당 {SEEDS}회)\n")
        for name, tension in CONTRASTS.items():
            res = run(1200, tension, WINDOWS, name == "중간", pool)
            print(f"### 대비 {name} (바깥 tension {tension}, 회복 구간 0.1)\n\n| 윈도우 | 겹침 | IoU | 적중률 | 계산 시간 |\n|---|---|---|---|---|")
            for k, arr in res.items():
                print(row(k, arr))
            print()
            sys.stdout.flush()

        windows = [45, 60, 90, 120, 180]
        minutes = [3, 4, 5, 6, 8, 10, 15, 20, 30]
        for name in ("약함", "중간"):
            print(f"## 3. 산책 길이별 적중률 (대비 {name})\n")
            print("산책이 윈도우보다 짧거나 같으면 점수가 하나뿐이라 구간을 고를 수 없다. 그 칸은 - 로 둔다.\n")
            print("| 산책 길이 | " + " | ".join(f"W={w}" for w in windows) + " |\n|---|" + "---|" * len(windows))
            for m in minutes:
                res = run(m * 60, CONTRASTS[name], windows, False, pool)
                cells = [f"{(res[w][:, 0] >= 0.8).mean() * 100:3.0f}%" if m * 60 > w else "-" for w in windows]
                print(f"| {m}분 | " + " | ".join(cells) + " |")
                sys.stdout.flush()
            print()

if __name__ == "__main__":
    main()
