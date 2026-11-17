"""스레드 k 개가 같은 계산을 동시에 돌릴 때 각자 걸린 시간. 동기 구조의 def 라우트(스레드 풀, GIL 공유)를 흉내 낸다.
사용(계산기 이미지 안): python concurrency.py <prefix|window> <샘플 수> <k>"""
import sys
import threading
import time

sys.path.insert(0, '/bench')
from calibrate import heart_rates, prefix
from services.stress_overview_service import build_stress_overview

algo, n, k = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
hr = heart_rates(n)
times = []


def one():
    started = time.perf_counter()
    prefix(hr) if algo == 'prefix' else build_stress_overview(hr, n)
    times.append(time.perf_counter() - started)


threads = [threading.Thread(target=one) for _ in range(k)]
for t in threads:
    t.start()
for t in threads:
    t.join()
print(algo, n, k, ' '.join(f'{t:.1f}' for t in sorted(times)), flush=True)
