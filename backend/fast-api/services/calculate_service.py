import numpy as np
import pyhrv.frequency_domain as fd
import pyhrv.time_domain as td


def get_single_stress(hr_data: list[float]):
    # NN 간격 계산
    nn_intervals = 60000 / np.array(hr_data)

    sdrr = td.sdnn(nn_intervals)['sdnn']
    rmssd = td.rmssd(nn_intervals)['rmssd']

    # mode='dev' 는 그래프를 만들지 않고 계산 값만 돌려준다
    freq_domain_features, _, _ = fd.welch_psd(nni=nn_intervals, mode='dev')
    lf_hf_ratio = freq_domain_features['fft_ratio']

    # 가중치 계산
    lf_hf_weight = get_lf_hf_weight(lf_hf_ratio)
    sdrr_weight = get_sdrr_weight(sdrr)
    rmssd_weight = get_rmssd_weight(rmssd)

    # 스트레스 지수 계산
    stress = lf_hf_weight + sdrr_weight + rmssd_weight
    return stress


def get_lf_hf_weight(lf_hf_ratio: float) -> int:
    if 1.35 <= lf_hf_ratio <= 1.55:
        return 2
    elif (1.2 <= lf_hf_ratio < 1.35) or (1.55 < lf_hf_ratio <= 1.7):
        return 4
    elif (1.1 <= lf_hf_ratio < 1.2) or (1.7 < lf_hf_ratio <= 1.81):
        return 6
    elif (1.0 <= lf_hf_ratio < 1.1) or (1.81 < lf_hf_ratio <= 1.93):
        return 8
    elif (0.9 <= lf_hf_ratio < 1.0) or (1.93 < lf_hf_ratio <= 2.04):
        return 10
    elif (0.8 <= lf_hf_ratio < 0.9) or (2.04 < lf_hf_ratio <= 2.16):
        return 12
    elif (0.7 <= lf_hf_ratio < 0.8) or (2.16 < lf_hf_ratio <= 2.28):
        return 14
    elif (0.6 <= lf_hf_ratio < 0.7) or (2.28 < lf_hf_ratio <= 2.4):
        return 16
    elif (0.5 <= lf_hf_ratio < 0.6) or (2.4 < lf_hf_ratio <= 2.5):
        return 18
    elif lf_hf_ratio < 0.5 or lf_hf_ratio > 2.5:
        return 20
    return 0


def get_sdrr_weight(sdrr: float) -> int:
    if 61.5 <= sdrr <= 68:
        return 2
    elif (55 <= sdrr < 61.5) or (68 < sdrr <= 75):
        return 4
    elif (48 <= sdrr < 55) or (75 < sdrr <= 83):
        return 6
    elif (40 <= sdrr < 48) or (83 < sdrr <= 90):
        return 8
    elif (30 <= sdrr < 40) or (90 < sdrr <= 100):
        return 10
    elif (20 <= sdrr < 30) or (100 < sdrr <= 110):
        return 12
    elif (15 <= sdrr < 20) or (110 < sdrr <= 115):
        return 14
    elif (10 <= sdrr < 15) or (115 < sdrr <= 120):
        return 16
    elif (7 <= sdrr < 10) or (120 < sdrr <= 125):
        return 18
    elif sdrr < 7 or sdrr > 125:
        return 20
    return 0


def get_rmssd_weight(rmssd: float) -> int:
    if 30 <= rmssd <= 33:
        return 2
    elif (27 <= rmssd < 30) or (33 < rmssd <= 36):
        return 4
    elif (24 <= rmssd < 27) or (36 < rmssd <= 40):
        return 6
    elif (21 <= rmssd < 24) or (40 < rmssd <= 44):
        return 8
    elif (15 <= rmssd < 21) or (44 < rmssd <= 48):
        return 10
    elif (15 <= rmssd < 30) or (48 < rmssd <= 52):
        return 12
    elif (12 <= rmssd < 15) or (52 < rmssd <= 56):
        return 14
    elif (10 <= rmssd < 12) or (56 < rmssd <= 60):
        return 16
    elif (8 <= rmssd < 10) or (60 < rmssd <= 65):
        return 18
    elif rmssd < 8 or rmssd > 65:
        return 20
    return 0


def get_windowed_stress_index(hr_data: list[float], window_size: int):
    """고정 길이 윈도우를 한 칸씩 밀며 스트레스 지수를 구한다.

    stress_arr[j] 는 hr_data[j : j + window_size] 구간의 스트레스다.
    샘플이 윈도우보다 적으면 전체를 한 구간으로 보고 값 하나만 돌려준다.
    """
    if len(hr_data) <= window_size:
        return [get_single_stress(hr_data)]
    return [get_single_stress(hr_data[j:j + window_size])
            for j in range(len(hr_data) - window_size + 1)]
