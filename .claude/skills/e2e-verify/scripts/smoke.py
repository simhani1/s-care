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
import base64
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://localhost:8080"
MGMT = "http://localhost:15672/api"
BACKEND = Path(__file__).resolve().parents[4] / "backend"
RUN = BACKEND / ".run"
DLQ = "request_queue.dlq"
SECRET_HEADER = "X-Internal-Secret"


def internal_secret():
    for line in (BACKEND / "api" / ".env").read_text().splitlines():
        if line.startswith("INTERNAL_API_SECRET="):
            return line.split("=", 1)[1].strip()
    raise AssertionError("backend/api/.env 에 INTERNAL_API_SECRET 이 없다")


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


def queues():
    out = compose("exec", "-T", "rabbitmq", "rabbitmqctl", "-q", "list_queues", "name", "messages",
                  "messages_unacknowledged")
    return {cols[0]: (int(cols[1]), int(cols[2])) for cols in (line.split() for line in out.splitlines()) if len(cols) == 3 and cols[1].isdigit()}


def queue_depth(name="request_queue"):
    q = queues()
    assert name in q, f"{name} 큐가 없다"
    return q[name][0]


def unacked(name="request_queue"):
    return queues()[name][1]


def mgmt(method, path, body=None):
    auth = base64.b64encode(b"scare:scare").decode()
    req = urllib.request.Request(MGMT + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def put_result(course_id, body, secret=None, token=None):
    headers = {SECRET_HEADER: secret} if secret is not None else {}
    status, _, _ = call("PUT", f"/internal/v1/walking/{course_id}/analysis-result", body, token, headers)
    return status


def log_lines(name, needle):
    return [line for line in (RUN / f"{name}.log").read_text().splitlines() if needle in line]


def pid(name):
    return int((RUN / f"{name}.pid").read_text())


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

    assert "response_queue" not in queues(), "response_queue 가 남아 있다"
    args = mgmt("GET", "/queues/%2F/request_queue")["arguments"]
    assert args == {"x-dead-letter-exchange": "", "x-dead-letter-routing-key": DLQ}, f"request_queue 인수 {args}"
    assert mgmt("GET", f"/queues/%2F/{DLQ}")["durable"], "데드레터 큐가 durable 이 아니다"


def scenario_outbox(n):
    token = login()
    worker = pid("worker")
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


def published_while_worker_stopped(token, n):
    """워커를 멈춘 채 저장하고 PUBLISHED 가 될 때까지 기다린다. 호출 측이 워커를 SIGCONT 해야 한다."""
    os.kill(pid("worker"), signal.SIGSTOP)
    course_id, _ = save(token, n)
    wait_for(lambda: outbox_status(course_id), lambda s: s == "PUBLISHED", timeout=30)
    return course_id


def course_row(course_id):
    return sql(f"SELECT analysis_status, max_stress, min_stress, healing_stress_avg, start_idx, end_idx "
               f"FROM walking_course WHERE walking_course_id = {course_id}")[0]


def scenario_spring_pause(n):
    token = login()
    base = queue_depth()
    spring = pid("spring")
    try:
        course_id = published_while_worker_stopped(token, n)
        os.kill(spring, signal.SIGSTOP)
        try:
            os.kill(pid("worker"), signal.SIGCONT)
            wait_for(lambda: log_lines("worker", f"retry courseId={course_id} "), bool, timeout=20)
            assert unacked() == 1, f"Spring 정지 중 미확인 메시지 {unacked()}개"
            assert course_row(course_id)[0] == "ANALYZING"
            print(f"Spring 정지 중 워커 재시도, 메시지 미확인 유지 courseId={course_id}")
        finally:
            os.kill(spring, signal.SIGCONT)
    finally:
        os.kill(pid("worker"), signal.SIGCONT)
    wait_for(lambda: course_status(token, course_id), lambda s: s == "COMPLETED", timeout=30)
    wait_for(lambda: log_lines("worker", f"acked courseId={course_id}"), bool, timeout=10)
    puts = log_lines("worker", f"PUT courseId={course_id} status=")
    assert puts[-1].endswith("status=200") and all(not p.endswith("status=200") for p in puts[:-1]), puts
    wait_for(lambda: (queue_depth(), unacked()), lambda v: v == (base, 0))
    assert outbox_status(course_id) == "COMPLETED"


def scenario_duplicate(n):
    token = login()
    secret = internal_secret()
    result = {"maxStress": 47, "minStress": 11, "healingStressAvg": 22.5, "startIdx": 1, "endIdx": 3}
    try:
        course_id = published_while_worker_stopped(token, n)
        statuses = []
        threads = [threading.Thread(target=lambda: statuses.append(put_result(course_id, result, secret)))
                   for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert statuses == [200] * 10, f"동시 호출 응답 {statuses}"
        assert put_result(course_id, {**result, "maxStress": 59}, secret) == 200, "완료 후 재호출이 200 이 아니다"
        applied = log_lines("spring", f"analysis result applied courseId={course_id}")
        assert len(applied) == 1, f"결과 반영 {len(applied)}회"
    finally:
        os.kill(pid("worker"), signal.SIGCONT)
    wait_for(lambda: log_lines("worker", f"acked courseId={course_id}"), bool, timeout=20)
    assert course_row(course_id) == ["COMPLETED", "47", "11", "22.5", "1", "3"], f"코스 {course_row(course_id)}"
    assert outbox_status(course_id) == "COMPLETED"
    print(f"동시 10건 + 재호출 + 워커 결과 모두 200, 반영 1회 courseId={course_id}")


def scenario_auth(n):
    token = login()
    secret = internal_secret()
    course_id, _ = save(token, n)
    wait_for(lambda: course_status(token, course_id), lambda s: s == "COMPLETED")
    before = course_row(course_id)
    result = {"maxStress": 1, "minStress": 1, "healingStressAvg": 1.0, "startIdx": 0, "endIdx": 0}
    cases = {
        "비밀 없음": put_result(course_id, result),
        "틀린 비밀": put_result(course_id, result, "wrong"),
        "사용자 JWT": put_result(course_id, result, token=token),
        "사용자 JWT + 틀린 비밀": put_result(course_id, result, secret + "x", token),
    }
    assert all(status == 403 for status in cases.values()), f"거부되지 않았다: {cases}"
    assert put_result(999999999, result, secret) == 404, "없는 코스가 404 가 아니다"
    assert put_result(course_id, {}, secret) == 400, "필드 없는 본문이 400 이 아니다"
    invalid = {
        "min > max": {**result, "maxStress": 5, "minStress": 9},
        "60 초과": {**result, "maxStress": 61},
        "음수 평균": {**result, "healingStressAvg": -1},
        "NaN 문자열": {**result, "healingStressAvg": "NaN"},
        "start > end": {**result, "startIdx": 5, "endIdx": 3},
        "좌표 수 이상": {**result, "startIdx": 0, "endIdx": n},
    }
    got = {name: put_result(course_id, body, secret) for name, body in invalid.items()}
    assert all(status == 400 for status in got.values()), f"검증 실패: {got}"
    assert put_result(course_id, {**result, "endIdx": n - 1, "futureField": 1}, secret) == 200, "모르는 필드를 거부했다"
    assert put_result(course_id, result, secret) == 200
    assert course_row(course_id) == before, "거부된 호출이 코스를 바꿨다"
    print(f"403 {list(cases)}, 404 없는 코스, 400 빈 본문과 {list(invalid)}, 모르는 필드는 200")


def scenario_poison(n):
    token = login()
    base = queue_depth(DLQ)
    short, _ = save(token, 3)
    body = walk_body(n)
    body["heartRates"] = [0] * n
    status, resp, _ = call("POST", "/api/v1/walking", body, token)
    assert status == 200, f"저장 실패: {status} {resp}"
    zero = resp["data"]
    good, _ = save(token, n)
    wait_for(lambda: course_status(token, good), lambda s: s == "COMPLETED")
    wait_for(lambda: queue_depth(DLQ), lambda d: d == base + 2, timeout=20)
    for c in (short, zero):
        assert course_status(token, c) == "ANALYZING", f"계산 실패 코스 {c} 가 {course_status(token, c)}"
        assert outbox_status(c) == "PUBLISHED"
    msgs = mgmt("POST", f"/queues/%2F/{DLQ}/get", {"count": 50, "ackmode": "reject_requeue_true", "encoding": "auto"})
    mine = [m for m in msgs if json.loads(m["payload"])["courseId"] in (short, zero)]
    assert len(mine) == 2, f"데드레터 큐에서 찾은 메시지 {len(mine)}개"
    for m in mine:
        assert m["properties"].get("delivery_mode") == 2, f"영속 메시지가 아니다: {m['properties']}"
        death = m["properties"]["headers"]["x-death"][0]
        assert (death["queue"], death["reason"]) == ("request_queue", "rejected"), death
    print(f"계산 실패 2건 데드레터, 뒤의 산책 {good} 은 완료")


def scenario_sweep(n):
    token = login()
    backdate = "UPDATE outbox SET updated_at = updated_at - INTERVAL 2 HOUR WHERE walking_course_id = {}"
    try:
        published = published_while_worker_stopped(token, n)
        sql(backdate.format(published))
        wait_for(lambda: (outbox_status(published), course_status(token, published)),
                 lambda v: v == ("FAILED", "FAILED"), timeout=30)
        print(f"PUBLISHED 1시간 초과 → FAILED courseId={published}")
    finally:
        os.kill(pid("worker"), signal.SIGCONT)
    wait_for(lambda: (outbox_status(published), course_status(token, published)),
             lambda v: v == ("COMPLETED", "COMPLETED"), timeout=30)
    print("늦게 도착한 결과로 COMPLETED")

    compose("stop", "rabbitmq")
    try:
        pending, _ = save(token, n)
        assert outbox_status(pending) == "PENDING"
        sql(backdate.format(pending))
        time.sleep(12)
        assert (outbox_status(pending), course_status(token, pending)) == ("PENDING", "ANALYZING"), \
            "1시간 넘은 PENDING 행을 실패 처리했다"
        print(f"PENDING 1시간 초과는 그대로 PENDING courseId={pending}")
    finally:
        compose("start", "rabbitmq")
    wait_for(lambda: course_status(token, pending), lambda s: s == "COMPLETED", timeout=120)
    assert outbox_status(pending) == "COMPLETED"
    print("브로커 복구 후 릴레이가 발행해 COMPLETED")


def stack(*args, **env):
    r = subprocess.run([str(Path(__file__).with_name("stack.sh")), *args], env={**os.environ, **env},
                       capture_output=True, text=True)
    assert r.returncode == 0, f"stack.sh {' '.join(args)} 실패: {r.stderr.strip()[-300:]}"


def alive(process_id):
    try:
        os.kill(process_id, 0)
        return True
    except ProcessLookupError:
        return False


def scenario_wrong_secret(n):
    token = login()
    base, dlq = queue_depth(), queue_depth(DLQ)
    stack("worker", INTERNAL_API_SECRET="wrong-secret")
    try:
        wrong = pid("worker")
        course_id, _ = save(token, n)
        wait_for(lambda: alive(wrong), lambda a: not a, timeout=30)
        assert queues()["request_queue"] == (base + 1, 0), f"request_queue {queues()['request_queue']}"
        assert queue_depth(DLQ) == dlq, "틀린 비밀로 데드레터됐다"
        assert len(log_lines("worker", f"PUT courseId={course_id} status=403")) == 1, "403 을 받고도 계속 소비했다"
        assert log_lines("worker", "Spring rejected INTERNAL_API_SECRET"), "ERROR 로그가 없다"
        assert outbox_status(course_id) == "PUBLISHED"
        print(f"403 한 번 뒤 워커 종료, 메시지는 request_queue 에 남음 courseId={course_id}")
    finally:
        stack("worker")
    wait_for(lambda: course_status(token, course_id), lambda s: s == "COMPLETED", timeout=30)
    assert queue_depth(DLQ) == dlq
    print("맞는 비밀로 재기동 후 COMPLETED")


def scenario_sweep_race(n, published=30, seconds=20, savers=3):
    """저장 부하 아래에서 실패 처리가 돌게 한다. 끝나면 부하용 산책은 큐를 비우고 아웃박스를 FAILED 로 둔다.
    FAILED 행이 많을수록 범위 잠금 회귀가 잘 드러나므로 코스 없는 FAILED 행 5000개를 먼저 넣는다."""
    sql("SET SESSION cte_max_recursion_depth = 10000; "
        "INSERT IGNORE INTO outbox (walking_course_id, payload, status, created_at, updated_at) "
        "WITH RECURSIVE seq(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM seq WHERE i < 5000) "
        "SELECT 1000000000 + i, '{}', 'FAILED', NOW(), NOW() FROM seq")
    token = login()
    sweeps_before = len(log_lines("spring", "OutboxFailureSweeper"))
    statuses = []
    try:
        os.kill(pid("worker"), signal.SIGSTOP)
        ids = [call("POST", "/api/v1/walking", walk_body(n), token)[1]["data"] for _ in range(published)]
        in_ids = ",".join(map(str, ids))
        wait_for(lambda: sql(f"SELECT COUNT(*) FROM outbox WHERE status = 'PUBLISHED' AND walking_course_id IN ({in_ids})"),
                 lambda r: r == [[str(published)]], timeout=30)
        stop = time.time() + seconds

        def saver():
            while time.time() < stop:
                statuses.append(call("POST", "/api/v1/walking", walk_body(130), token)[0])

        threads = [threading.Thread(target=saver) for _ in range(savers)]
        for t in threads:
            t.start()
        for i in range(0, published, 3):
            sql("UPDATE outbox SET updated_at = updated_at - INTERVAL 2 HOUR "
                f"WHERE walking_course_id IN ({','.join(map(str, ids[i:i + 3]))})")
            time.sleep(seconds / (published / 3))
        for t in threads:
            t.join()
    finally:
        sql(f"UPDATE outbox SET status = 'FAILED' WHERE status IN ('PENDING', 'PUBLISHED') AND walking_course_id > {max(ids)}")
        sql("UPDATE walking_course SET analysis_status = 'FAILED' WHERE analysis_status = 'ANALYZING' "
            f"AND walking_course_id > {max(ids)}")
        os.kill(pid("worker"), signal.SIGCONT)
    failed = [st for st in statuses if st != 200]
    print(f"실패 처리 중 저장 {len(statuses)}건, 200 아닌 것 {len(failed)}건")
    assert not failed, f"저장 실패 {len(failed)}건: {sorted(set(failed))}"
    assert len(log_lines("spring", "OutboxFailureSweeper")) > sweeps_before, "실패 처리가 돌지 않았다"
    wait_for(lambda: sql(f"SELECT o.status, c.analysis_status, COUNT(*) FROM outbox o JOIN walking_course c "
                         f"ON c.walking_course_id = o.walking_course_id WHERE o.walking_course_id IN ({in_ids}) "
                         "GROUP BY 1, 2"),
             lambda r: r == [["COMPLETED", "COMPLETED", str(published)]], timeout=60)
    compose("exec", "-T", "rabbitmq", "rabbitmqctl", "-q", "purge_queue", "request_queue")


SCENARIOS = {"basic": scenario_basic, "outbox": scenario_outbox, "broker-outage": scenario_broker_outage,
             "concurrent": scenario_concurrent, "broker-hang": scenario_broker_hang,
             "spring-pause": scenario_spring_pause, "duplicate": scenario_duplicate, "auth": scenario_auth,
             "poison": scenario_poison, "sweep": scenario_sweep, "wrong-secret": scenario_wrong_secret,
             "sweep-race": scenario_sweep_race}

if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "basic"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    SCENARIOS[name](n)
    print(f"통과: {name}")
