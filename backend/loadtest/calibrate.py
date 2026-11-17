"""계산 한 건의 소요 시간을 잰다. 계산기 이미지 안에서 돌린다 (bench.py calibrate 가 docker run --cpus 로 부른다).
사용: python calibrate.py <prefix|window> <샘플 수> [반복]"""
import math
import random
import sys
import time

sys.path.insert(0, '/app')
from services.calculate_service import get_single_stress
from services.stress_overview_service import build_stress_overview


def heart_rates(n):
    rng = random.Random(n)
    return [round(105 + 8 * math.sin(i / 40) + rng.gauss(0, 4)) for i in range(n)]


def prefix(hr):
    return [get_single_stress(hr[:i]) for i in range(4, len(hr) + 1)]


if __name__ == '__main__':
    algo, n, repeat = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 1
    hr = heart_rates(n)
    for _ in range(repeat):
        started = time.perf_counter()
        prefix(hr) if algo == 'prefix' else build_stress_overview(hr, n)
        print(f'{algo} {n} {time.perf_counter() - started:.2f}', flush=True)
