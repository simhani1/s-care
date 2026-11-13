import numpy as np

from exceptions.custom_exceptions import CalculateFailedException
from models.response_models import StressOverview
from services.calculate_service import get_windowed_stress_index

# 스트레스 한 점을 계산할 때 보는 심박 샘플 수. 근거는 experiments/RESULTS.md
WINDOW_SIZE = 120
# 이보다 짧은 산책은 힐링 구간을 제공하지 않는다 (초)
MIN_HEALING_WALK_SECONDS = 300
SECTION_DIVISOR = 3


def find_healing_course_idx(stress_arr: list[float], section_len: int = None):
    """평균 스트레스가 가장 낮은 연속 구간을 찾는다.

    반환값은 (구간 평균, 시작 인덱스, 끝 인덱스)이며 인덱스는 stress_arr 기준, 끝 포함이다.
    동률이면 가장 앞 구간을 고른다.
    """
    size = len(stress_arr)
    if section_len is None:
        section_len = size // SECTION_DIVISOR
    section_len = max(1, min(section_len, size))

    prefix = np.concatenate(([0.0], np.cumsum(stress_arr, dtype=float)))
    section_avgs = (prefix[section_len:] - prefix[:-section_len]) / section_len
    # 누적합의 부동소수 오차가 동률을 깨지 않게 반올림한 값으로 고른다
    start_idx = int(np.argmin(np.round(section_avgs, 9)))
    return float(section_avgs[start_idx]), start_idx, start_idx + section_len - 1


def locate_healing_section(stress_arr: list[float], window_size: int):
    """힐링 구간을 심박(=위치 좌표) 배열 기준 인덱스로 돌려준다.

    stress_arr[j] 는 윈도우 hr_data[j : j + window_size] 의 값이라 윈도우 중심으로 옮긴다.
    """
    avg, start_idx, end_idx = find_healing_course_idx(stress_arr)
    center = window_size // 2
    return avg, start_idx + center, end_idx + center


def build_stress_overview(hr_data: list[float], walking_time: int) -> StressOverview:
    """산책 한 건의 심박으로 최대/최소 스트레스와 힐링 구간을 구한다.

    start_idx, end_idx 는 hr_data(=위치 좌표) 기준 인덱스다.
    """
    if len(hr_data) < 4:  # 3차 보간에 필요한 최소 샘플 수
        raise CalculateFailedException()
    stress_arr = get_windowed_stress_index(hr_data, WINDOW_SIZE)

    healing_stress_avg, start_idx, end_idx = 0.0, 0, 0
    # 샘플이 윈도우 두 개 분량은 되어야 비교할 구간이 생긴다. 심박이 드물게 들어온 산책에서
    # 한두 점짜리 구간이 나오는 것을 막는다.
    if walking_time >= MIN_HEALING_WALK_SECONDS and len(hr_data) >= 2 * WINDOW_SIZE:
        healing_stress_avg, start_idx, end_idx = locate_healing_section(stress_arr, WINDOW_SIZE)

    return StressOverview(
        max_stress=max(stress_arr),
        min_stress=min(stress_arr),
        stress_indices=stress_arr,
        healing_stress_avg=healing_stress_avg,
        start_idx=start_idx,
        end_idx=end_idx
    )
