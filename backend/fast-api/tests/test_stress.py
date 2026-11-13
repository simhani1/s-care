"""실행: python -m tests.test_stress  (backend/fast-api 에서, pytest 로도 돌아간다)"""
import numpy as np

from experiments.synthetic import make_walk
from services.calculate_service import get_single_stress, get_windowed_stress_index
from services.stress_overview_service import (WINDOW_SIZE, build_stress_overview,
                                              find_healing_course_idx)


def _brute_force(arr, length):
    avgs = [sum(arr[i:i + length]) / length for i in range(len(arr) - length + 1)]
    start = min(range(len(avgs)), key=lambda i: (round(avgs[i], 9), i))
    return start, start + length - 1


def test_healing_section_matches_brute_force():
    rng = np.random.default_rng(7)
    cases = {
        "앞쪽이 최저": [10] * 30 + [40] * 60,     # 예전 구현은 None 인덱스를 돌려줬다
        "가운데가 최저": [40] * 30 + [10] * 30 + [40] * 30,
        "뒤쪽이 최저": [40] * 60 + [10] * 30,
        "랜덤": [int(x) for x in rng.integers(6, 60, 90)],
    }
    for name, arr in cases.items():
        avg, start, end = find_healing_course_idx(arr)
        assert (start, end) == _brute_force(arr, len(arr) // 3), name
        assert abs(avg - sum(arr[start:end + 1]) / (end - start + 1)) < 1e-9, name


def test_window_reads_only_its_own_samples():
    hr = make_walk(400, None, np.random.default_rng(1))
    stress = get_windowed_stress_index(hr, 60)
    assert len(stress) == 400 - 60 + 1
    assert stress[100] == get_single_stress(hr[100:160])


def test_chunked_calculation_equals_batch():
    """직전 window-1 개 샘플만 이어 붙이면 나눠 계산해도 일괄 계산과 같다."""
    hr = make_walk(500, None, np.random.default_rng(2))
    w = 60
    batch = get_windowed_stress_index(hr, w)
    chunked = []
    for start in range(0, len(batch), 97):               # 임의 크기로 쪼갠다
        end = min(start + 97, len(batch))
        chunked += get_windowed_stress_index(hr[start:end + w - 1], w)
    assert chunked == batch


def test_short_walk_yields_single_value_without_healing_section():
    hr = make_walk(WINDOW_SIZE - 10, None, np.random.default_rng(3))
    overview = build_stress_overview(hr, walking_time=WINDOW_SIZE - 10)
    assert overview.max_stress == overview.min_stress
    assert (overview.start_idx, overview.end_idx, overview.healing_stress_avg) == (0, 0, 0.0)


def test_overview_finds_planted_healing_section():
    n, truth = 1200, (500, 900)
    hr = make_walk(n, truth, np.random.default_rng(4), base_tension=0.5)
    overview = build_stress_overview(hr, walking_time=n)
    assert 0 <= overview.start_idx <= overview.end_idx < n
    inside = min(overview.end_idx + 1, truth[1]) - max(overview.start_idx, truth[0])
    assert inside / (overview.end_idx + 1 - overview.start_idx) >= 0.8
    assert overview.min_stress < overview.max_stress


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore")
    tests = [f for name, f in sorted(globals().items()) if name.startswith("test_")]
    for t in tests:
        t()
        print("ok", t.__name__)
    print(f"{len(tests)} passed")
