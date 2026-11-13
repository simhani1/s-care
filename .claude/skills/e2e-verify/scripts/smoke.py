"""종단 간 시나리오. 표준 라이브러리만 쓴다.

사용: python3 smoke.py [시나리오] [심박 샘플 수]
실패하면 0 이 아닌 코드로 끝난다. PR 이 진행되면서 시나리오를 여기에 추가한다.
"""
import json
import math
import os
import random
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
BACKEND = Path(__file__).resolve().parents[4] / "backend"


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


def compose(*args):
    r = subprocess.run(["docker", "compose", *args], cwd=BACKEND, capture_output=True, text=True)
    assert r.returncode == 0, f"docker compose {' '.join(args)} 실패: {r.stderr.strip()[-300:]}"
    return r.stdout


def sql(query):
    out = compose("exec", "-T", "mysql", "mysql", "-uscare", "-pscare", "scare", "-N", "-e", query)
    return [line.split("\t") for line in out.splitlines()]


def outbox_status(course_id):
    rows = sql(f"SELECT status FROM outbox WHERE walking_course_id = {course_id}")
    assert len(rows) == 1, f"아웃박스 행 {len(rows)}개"
    return rows[0][0]


def queue_depth(name="request_queue"):
    for line in compose("exec", "-T", "rabbitmq", "rabbitmqctl", "-q", "list_queues", "name", "messages").splitlines():
        cols = line.split()
        if cols and cols[0] == name:
            return int(cols[1])
    raise AssertionError(f"{name} 큐가 없다")


def save(token, n):
    started = time.time()
    status, body, _ = call("POST", "/api/v1/walking", walk_body(n), token)
    elapsed = time.time() - started
    assert status == 200, f"저장 실패: {status} {body}"
    print(f"저장 {elapsed:.2f}s courseId={body['data']}")
    return body["data"], elapsed


def course_status(token, course_id):
    status, body, _ = call("GET", f"/api/v1/walking/detail/{course_id}", token=token)
    assert status == 200, f"상세 조회 실패: {status} {body}"
    return body["data"]["analysisStatus"]


def scenario_basic(n):
    token = login()
    started = time.time()
    course_id, _ = save(token, n)
    first = course_status(token, course_id)
    assert first in ("ANALYZING", "COMPLETED"), f"저장 직후 상태 {first}"

    sent = walk_body(n)["locations"]
    pos = {}

    def detail():
        status, body, _ = call("GET", f"/api/v1/walking/detail/{course_id}", token=token)
        assert status == 200, f"상세 조회 실패: {status} {body}"
        data = body["data"]
        pos["list"] = data["posList"]
        data["posList"] = len(data["posList"])
        return data

    data = wait_for(detail, lambda d: d["analysisStatus"] == "COMPLETED")
    print(f"결과 반영 {time.time() - started:.2f}s {data}")
    assert data["posList"] == n, f"좌표 수 {data['posList']} != {n}"
    for i in (0, n // 2, n - 1):
        got, want = pos["list"][i], sent[i]
        assert math.isclose(got["lat"], want["latitude"]) and math.isclose(got["lng"], want["longitude"]), \
            f"좌표[{i}] {got} != {want}"
    assert data["minStress"] <= data["maxStress"]
    assert 0 <= data["startIdx"] <= data["endIdx"] < n, "힐링 구간 인덱스가 좌표 범위를 벗어났다"

    status, body, _ = call("GET", "/api/v1/walking/list?page=0&size=5", token=token)
    listed = [c for c in body["data"] if c["courseId"] == course_id] if status == 200 else []
    assert listed, "목록에 코스가 없다"
    assert listed[0]["analysisStatus"] == "COMPLETED", f"목록 상태 {listed[0]['analysisStatus']}"
    assert outbox_status(course_id) == "COMPLETED", f"아웃박스 {outbox_status(course_id)}"


def scenario_outbox(n):
    token = login()
    worker = int((BACKEND / ".run" / "worker.pid").read_text())
    base = queue_depth()
    os.kill(worker, signal.SIGSTOP)
    try:
        course_id, _ = save(token, n)
        wait_for(lambda: outbox_status(course_id), lambda s: s == "PUBLISHED", timeout=30)
        assert course_status(token, course_id) == "ANALYZING"
        time.sleep(12)
        assert outbox_status(course_id) == "PUBLISHED"
        depth = queue_depth()
        assert depth - base == 1, f"발행된 메시지 {depth - base}개"
        print(f"발행됨 유지, 큐 메시지 1개 courseId={course_id}")
    finally:
        os.kill(worker, signal.SIGCONT)
    wait_for(lambda: course_status(token, course_id), lambda s: s == "COMPLETED")
    assert outbox_status(course_id) == "COMPLETED"
    wait_for(queue_depth, lambda d: d == base)


def scenario_broker_outage(n):
    token = login()
    compose("stop", "rabbitmq")
    try:
        course_id, elapsed = save(token, n)
        assert elapsed < 2, f"저장이 {elapsed:.2f}s 걸렸다"
        assert course_status(token, course_id) == "ANALYZING"
        assert outbox_status(course_id) == "PENDING"
    finally:
        compose("start", "rabbitmq")
    print("브로커 재기동")
    started = time.time()
    wait_for(lambda: course_status(token, course_id), lambda s: s == "COMPLETED", timeout=120)
    print(f"브로커 복구 후 {time.time() - started:.1f}s 에 완료")
    assert outbox_status(course_id) == "COMPLETED"


def wait_all_completed(token, course_ids, timeout):
    pending = set(course_ids)

    def left():
        pending.difference_update([c for c in list(pending) if course_status(token, c) == "COMPLETED"])
        return sorted(pending)

    wait_for(left, lambda rest: not rest, timeout=timeout)
    rows = sql(f"SELECT status, COUNT(*) FROM outbox WHERE walking_course_id IN ({','.join(map(str, course_ids))}) "
               "GROUP BY status")
    assert rows == [["COMPLETED", str(len(course_ids))]], f"아웃박스 {rows}"


def scenario_concurrent(n, count=30, bound=3.0):
    token = login()
    results = []

    def one():
        started = time.time()
        status, body, _ = call("POST", "/api/v1/walking", walk_body(n), token)
        results.append((status, time.time() - started, body["data"] if status == 200 else str(body)[:80]))

    threads = [threading.Thread(target=one) for _ in range(count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    slowest = max(r[1] for r in results)
    failed = [r for r in results if r[0] != 200]
    print(f"동시 저장 {count}건, 200 {count - len(failed)}건, 최대 {slowest:.2f}s")
    assert not failed, f"실패 {len(failed)}건: {failed[0]}"
    assert slowest < bound, f"최대 {slowest:.2f}s >= {bound}s"
    wait_all_completed(token, [r[2] for r in results], timeout=60)


def scenario_broker_hang(n):
    token = login()
    course_ids = []
    compose("pause", "rabbitmq")
    try:
        for _ in range(3):
            course_id, elapsed = save(token, n)
            assert elapsed < 1, f"저장이 {elapsed:.2f}s 걸렸다"
            course_ids.append(course_id)
        time.sleep(12)
        course_id, elapsed = save(token, n)
        assert elapsed < 1, f"스케줄러가 도는 중 저장이 {elapsed:.2f}s 걸렸다"
        course_ids.append(course_id)
        assert all(course_status(token, c) == "ANALYZING" for c in course_ids)
    finally:
        compose("unpause", "rabbitmq")
    print("브로커 재개")
    started = time.time()
    wait_all_completed(token, course_ids, timeout=120)
    print(f"브로커 재개 후 {time.time() - started:.1f}s 에 모두 완료")


SCENARIOS = {"basic": scenario_basic, "outbox": scenario_outbox, "broker-outage": scenario_broker_outage,
             "concurrent": scenario_concurrent, "broker-hang": scenario_broker_hang}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "basic"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    SCENARIOS[name](n)
    print(f"통과: {name}")
