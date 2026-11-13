import numpy as np
import scipy as sp
from scipy.signal import welch


def get_single_stress(hr_data: list[float]):
    # NN 간격 계산
    nn_intervals = 60000 / np.array(hr_data)

    # SDRR 계산
    sdrr = get_sdrr(nn_intervals)

    # RMSSD 계산
    rmssd_result = get_rmssd(nn_intervals)
    rmssd = rmssd_result['rmssd']

    freq_domain_features = welch_psd(nn_intervals)
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


def get_sdrr(nn_intervals):
    sdrr = np.std(nn_intervals, ddof=1)
    return sdrr


def nn_formats(nni):
    nn_ = np.asarray(nni, dtype='float64')
    # 데이터가 [초] 단위로 식별되었으면 변환하고, 그렇지 않으면 NumPy 배열 형식이 맞는지 확인
    if np.max(nn_) < 10:
        nn_ = [int(x * 1000) for x in nn_]
    return np.asarray(nn_)


def get_rmssd(nni=None):
    nnd = nni_diff(nni)
    rmssd_ = np.sum([x ** 2 for x in nnd])
    rmssd_ = np.sqrt(1. / nnd.size * rmssd_)
    return {'rmssd': rmssd_}


def nni_diff(nni):
    nn = nn_formats(nni)
    nn_diff_ = np.zeros(nn.size - 1)
    for i in range(nn.size - 1):
        nn_diff_[i] = abs(nn[i + 1] - nn[i])
    return np.asarray(nn_diff_)


def welch_psd(nni=None,
              nfft=2 ** 12,
              window='hamming',
              mode='normal',
              fbands=None):
    fbands = _check_freq_bands(fbands)
    fs = 4
    t = np.cumsum(nni)
    t -= t[0]
    f_interpol = sp.interpolate.interp1d(t, nni, 'cubic')
    t_interpol = np.arange(t[0], t[-1], 1000. / fs)
    nn_interpol = f_interpol(t_interpol)

    # DC 오프셋 억제를 위해 각 샘플에서 평균값을 빼기
    nn_interpol = nn_interpol - np.mean(nn_interpol)

    # NNI 시리즈의 총 기간에 따라 'nperseg'를 조정 (5분 임계값 = 300000ms)
    if t.max() < 300000:
        nperseg = min(nfft, nn_interpol.size)
    else:
        nperseg = 300

    # 주파수 분석을 통한 LF/HF 비율 계산
    frequencies, powers = welch(
        x=nn_interpol,
        fs=fs,
        window=window,
        nperseg=nperseg,
        nfft=nfft,
        scaling='density'
    )

    # Metadata
    meta = {
        'fft_nfft': nfft,
        'fft_window': window,
        'fft_resampling_frequency': fs,
        'fft_interpolation': 'cubic'
    }

    params, freq_i = _compute_parameters('fft', frequencies, powers, fbands)
    return {**params, **meta}


def _check_freq_bands(freq_bands):
    vlf = (0.000, 0.04)
    lf = (0.04, 0.15)
    hf = (0.15, 0.4)
    return {'vlf': vlf, 'lf': lf, 'hf': hf}


def _compute_parameters(method, frequencies, power, freq_bands):
    # 주파수 해상도 계산
    df = (frequencies[1] - frequencies[0])

    # 주어진 주파수 대역 내의 주파수 값 인덱스 가져오기
    vlf_i, lf_i, hf_i = _get_frequency_indices(frequencies, freq_bands)
    vlf_f, lf_f, hf_f = _get_frequency_arrays(frequencies, vlf_i, lf_i, hf_i)

    # 파워의 절댓값
    vlf_power = np.sum(power[vlf_i]) * df
    lf_power = np.sum(power[lf_i]) * df
    hf_power = np.sum(power[hf_i]) * df
    abs_powers = (vlf_power, lf_power, hf_power,)
    total_power = np.sum(abs_powers)

    vlf_peak = vlf_f[np.argmax(power[vlf_i])]
    lf_peak = lf_f[np.argmax(power[lf_i])]
    hf_peak = hf_f[np.argmax(power[hf_i])]
    peaks = (vlf_peak, lf_peak, hf_peak,)

    # 상대적, 로그 스케일 파워 및 LF/HF 비율
    rels = tuple([float(x) / total_power * 100 for x in abs_powers])
    logs = tuple([float(np.log(x)) for x in abs_powers])
    ratio = float(lf_power) / hf_power

    # 정규화된 파워
    norms = tuple([100 * x / (lf_power + hf_power) for x in [lf_power, hf_power]])

    params = {
        '%s_bands' % method: freq_bands,
        '%s_peak' % method: peaks,
        '%s_abs' % method: abs_powers,
        '%s_rel' % method: rels,
        '%s_log' % method: logs,
        '%s_norm' % method: norms,
        '%s_ratio' % method: ratio,
        '%s_total' % method: total_power
    }
    freq_i = {'vlf': vlf_i, 'lf': lf_i, 'hf': hf_i}
    return params, freq_i


def _get_frequency_indices(freq, freq_bands):
    indices = []
    for key in freq_bands.keys():
        if freq_bands[key] is None:
            indices.append(None)
        else:
            indices.append(np.where((freq_bands[key][0] <= freq) & (freq <= freq_bands[key][1])))

    return indices[0][0], indices[1][0], indices[2][0]


def _get_frequency_arrays(freq, vlf_i, lf_i, hf_i):
    vlf_f = np.asarray(freq[vlf_i])
    lf_f = np.asarray(freq[lf_i])
    hf_f = np.asarray(freq[hf_i])
    return vlf_f, lf_f, hf_f


def get_windowed_stress_index(hr_data: list[float], window_size: int):
    """고정 길이 윈도우를 한 칸씩 밀며 스트레스 지수를 구한다.

    stress_arr[j] 는 hr_data[j : j + window_size] 구간의 스트레스다.
    샘플이 윈도우보다 적으면 전체를 한 구간으로 보고 값 하나만 돌려준다.
    """
    if len(hr_data) <= window_size:
        return [get_single_stress(hr_data)]
    return [get_single_stress(hr_data[j:j + window_size])
            for j in range(len(hr_data) - window_size + 1)]
