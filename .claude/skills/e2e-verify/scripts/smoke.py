"""종단 간 시나리오. 표준 라이브러리만 쓴다.

사용: python3 smoke.py [시나리오] [심박 샘플 수]
실패하면 0 이 아닌 코드로 끝난다. PR 이 진행되면서 시나리오를 여기에 추가한다.
"""
import json
import math
import random
import sys
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8080"


def call(method, path, body=None, token=None, headers=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, method=method, data=data, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500], {}


def login(email="smoke@test.com"):
    status, body, headers = call("POST", "/api/v1/members/auth/login",
                                 {"email": email, "nickname": "smoke", "profileUrl": "x", "provider": "google"})
    assert status == 200, f"로그인 실패: {status} {body}"
    return headers["Authorization"]


def walk_body(n):
    """n 초 분량의 산책. 심박과 좌표가 1초에 하나씩이다."""
    rng = random.Random(n)
    return {
        "startedAt": "2026-01-01T10:00:00",
        "finishedAt": time.strftime("2026-01-01T%H:%M:%S", time.gmtime(10 * 3600 + n)),
        "heartRates": [round(105 + 8 * math.sin(i / 40) + rng.gauss(0, 4)) for i in range(n)],
        "locations": [{"latitude": 37.5 + i * 1e-5, "longitude": 127.0 + i * 1e-5} for i in range(n)],
    }


def wait_for(fetch, done, timeout=30.0):
    deadline = time.time() + timeout
    while True:
        value = fetch()
        if done(value):
            return value
        assert time.time() < deadline, f"{timeout}초 안에 조건을 만족하지 못했다. 마지막 값: {value}"
        time.sleep(0.25)


def scenario_basic(n):
    """산책 저장 후 스트레스 결과가 상세 조회에 반영되고, 힐링 구간이 좌표 범위 안에 있다."""
    token = login()
    started = time.time()
    status, body, _ = call("POST", "/api/v1/walking", walk_body(n), token)
    assert status == 200, f"저장 실패: {status} {body}"
    course_id = body["data"]
    print(f"저장 {time.time() - started:.2f}s courseId={course_id}")

    def detail():
        status, body, _ = call("GET", f"/api/v1/walking/detail/{course_id}", token=token)
        assert status == 200, f"상세 조회 실패: {status} {body}"
        data = body["data"]
        data["posList"] = len(data["posList"])   # 실패 메시지에 좌표 전체가 찍히지 않게 개수만 남긴다
        return data

    data = wait_for(detail, lambda d: d["maxStress"] != 0)
    print(f"결과 반영 {time.time() - started:.2f}s {data}")
    assert data["posList"] == n, f"좌표 수 {data['posList']} != {n}"
    assert data["minStress"] <= data["maxStress"]
    assert 0 <= data["startIdx"] <= data["endIdx"] < n, "힐링 구간 인덱스가 좌표 범위를 벗어났다"

    status, body, _ = call("GET", "/api/v1/walking/list?page=0&size=5", token=token)
    assert status == 200 and any(c["courseId"] == course_id for c in body["data"]), "목록에 코스가 없다"


SCENARIOS = {"basic": scenario_basic}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "basic"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    SCENARIOS[name](n)
    print(f"통과: {name}")
