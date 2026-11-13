"""실험용 합성 심박 생성기.

실제 산책 심박 기록이 없어서, 심박 변이도(HRV)를 조절할 수 있는 합성 신호로 대신한다.
박동 간격(NN)을 느린 추세 + LF 진동(약 0.1Hz) + HF 진동(약 0.25Hz) + 잡음으로 만들고
bpm 으로 바꾼다. tension 이 0 이면 변이도가 크고(회복), 1 이면 변이도가 눌린다(긴장).
"""
import numpy as np

LF_HZ, HF_HZ = 0.10, 0.22


def _state(tension: float):
    """tension(0~1) -> (LF 진폭, HF 진폭, 잡음 표준편차) [ms]"""
    scale = 1.0 - 0.85 * tension            # 긴장할수록 전체 변이도 감소
    lf_hf_amp_ratio = 1.2 + 1.0 * tension   # 긴장할수록 LF 우세
    hf = 52.0 * scale
    return hf * lf_hf_amp_ratio, hf, 4.0 + 2.0 * tension


def make_walk(n: int, healing: tuple[int, int] | None, rng, *,
              base_tension=0.7, healing_tension=0.1, round_bpm=True):
    """n 개 샘플의 심박(bpm)을 만든다. healing=(start, end) 구간만 tension 이 낮다."""
    tension = np.full(n, base_tension)
    if healing:
        s, e = healing
        tension[s:e] = healing_tension
        k = np.ones(15) / 15                 # 상태 전환을 15샘플에 걸쳐 완만하게
        tension = np.convolve(np.pad(tension, 7, mode='edge'), k, mode='valid')

    # 평균 심박의 느린 추세: 95~115bpm 사이를 몇 분 주기로 오르내림
    mean_hr = 105 + 7 * np.sin(2 * np.pi * np.arange(n) / rng.uniform(240, 600) + rng.uniform(0, 6.28)) \
        + np.cumsum(rng.normal(0, 0.05, n))
    base_nn = 60000.0 / mean_hr

    nn = np.empty(n)
    t = 0.0
    ph_lf, ph_hf = rng.uniform(0, 6.28, 2)
    for i in range(n):
        a_lf, a_hf, sigma = _state(tension[i])
        nn[i] = base_nn[i] + a_lf * np.sin(ph_lf) + a_hf * np.sin(ph_hf) + rng.normal(0, sigma)
        nn[i] = max(nn[i], 300.0)
        dt = nn[i] / 1000.0
        # 위상에 잡음을 섞어 완전한 정현파가 되지 않게 한다
        ph_lf += 2 * np.pi * LF_HZ * dt + rng.normal(0, 0.08)
        ph_hf += 2 * np.pi * HF_HZ * dt + rng.normal(0, 0.12)
        t += dt
    hr = 60000.0 / nn
    return list(np.round(hr) if round_bpm else hr)
