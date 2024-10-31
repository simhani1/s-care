import numpy as np
import pyhrv.time_domain as td
import pyhrv.frequency_domain as fd
from exceptions.custom_exceptions import CalculateFailedException

def get_single_stress_index(hr_data):
    try:
        # NN 간격 계산
        nn_intervals = 60000 / np.array(hr_data)

        # RMSSD 계산
        rmssd_result = td.rmssd(nn_intervals)
        rmssd = rmssd_result['rmssd']

        # 주파수 분석을 통한 LF/HF 비율 계산
        freq_domain_features = fd.welch_psd(nni=nn_intervals, show=False)
        lf_hf_ratio = freq_domain_features['fft_ratio']

        # 스트레스 지수 계산
        stress_index = lf_hf_ratio / rmssd if rmssd != 0 else None
        return stress_index
    except Exception as e:
        raise CalculateFailedException
