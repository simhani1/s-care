"""산책 저장 흐름 부하 테스트. 표준 라이브러리만 쓴다.

사용 (저장소 루트에서, 로컬 스택이 떠 있어야 한다):
  python3 backend/loadtest/loadtest.py ramp       유입량을 올리며 저장 응답과 완료 지연을 잰다 (워커 1대)
  python3 backend/loadtest/loadtest.py scale      밀린 산책을 워커 1, 2, 4대로 소화하는 처리량을 잰다
  python3 backend/loadtest/loadtest.py outage     워커가 죽은 동안 저장하고, 되살린 뒤 유실이 없는지 본다
"""
import base64
import http.client
import json
import math
import os
import random
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
WORKER_DIR = f"{ROOT}/backend/fast-api"
RUN_DIR = f"{ROOT}/backend/.run"
WALK_SECONDS = 1800
local = threading.local()


def walk_body(n):
    rng = random.Random(n)
    return json.dumps({
        "startedAt": "2026-01-01T10:00:00",
        "finishedAt": time.strftime("2026-01-01T%H:%M:%S", time.gmtime(10 * 3600 + n)),
        "heartRates": [round(105 + 8 * math.sin(i / 40) + rng.gauss(0, 4)) for i in range(n)],
        "locations": [{"latitude": 37.5 + i * 1e-5, "longitude": 127.0 + i * 1e-5} for i in range(n)],
    }).encode()


def login():
    conn = http.client.HTTPConnection("localhost", 8080)
    conn.request("POST", "/api/v1/members/auth/login", headers={"Content-Type": "application/json"},
                 body=json.dumps({"email": "load@test.com", "nickname": "load", "profileUrl": "x", "provider": "google"}))
    res = conn.getresponse()
    res.read()
    return res.getheader("Authorization")


def save(token, body):
    if not hasattr(local, "conn"):
        local.conn = http.client.HTTPConnection("localhost", 8080, timeout=60)
    started = time.perf_counter()
    try:
        local.conn.request("POST", "/api/v1/walking", body=body,
                           headers={"Content-Type": "application/json", "Authorization": token})
        res = local.conn.getresponse()
        data = res.read()
        course_id = json.loads(data)["data"] if res.status == 200 else None
        return res.status, time.perf_counter() - started, course_id
    except Exception:
        local.conn.close()
        del local.conn
        return 0, time.perf_counter() - started, None


def fire(token, body, rate, seconds, pool):
    """고정 유입량(open loop): 응답이 늦어도 다음 요청을 제때 보낸다."""
    count = int(rate * seconds)
    start = time.perf_counter()
    futures = []
    for i in range(count):
        delay = start + i / rate - time.perf_counter()
        if delay > 0:
            time.sleep(delay)
        futures.append(pool.submit(save, token, body))
    return [f.result() for f in futures]


def sql(query):
    out = subprocess.run(["docker", "compose", "exec", "-T", "mysql", "mysql", "-uscare", "-pscare", "scare", "-N", "-e", query],
                         cwd=f"{ROOT}/backend", capture_output=True, text=True).stdout
    return [line.split("\t") for line in out.strip().splitlines() if line]


def queue_depth():
    conn = http.client.HTTPConnection("localhost", 15672, timeout=5)
    auth = base64.b64encode(b"scare:scare").decode()
    conn.request("GET", "/api/queues/%2F/request_queue", headers={"Authorization": f"Basic {auth}"})
    data = json.loads(conn.getresponse().read())
    return data.get("messages_ready", 0), data.get("messages_unacknowledged", 0)


def wait_done(ids, timeout=900):
    """모든 코스가 분석 중을 벗어날 때까지 기다리며 큐 길이의 최댓값을 잰다."""
    lo, hi = min(ids), max(ids)
    peak = 0
    deadline = time.time() + timeout
    while time.time() < deadline:
        peak = max(peak, sum(queue_depth()))
        left = int(sql(f"SELECT COUNT(*) FROM walking_course WHERE walking_course_id BETWEEN {lo} AND {hi} "
                       "AND analysis_status = 'ANALYZING'")[0][0])
        if left == 0:
            return peak
        time.sleep(1)
    raise TimeoutError(f"{left} walks still analyzing")


def completion(ids):
    """코스 생성부터 결과 반영까지 걸린 시간(초)과 상태별 건수."""
    lo, hi = min(ids), max(ids)
    rows = sql("SELECT o.status, TIMESTAMPDIFF(MICROSECOND, c.created_at, o.updated_at) / 1e6, "
               "UNIX_TIMESTAMP(o.updated_at) FROM walking_course c JOIN outbox o USING (walking_course_id) "
               f"WHERE c.walking_course_id BETWEEN {lo} AND {hi}")
    states = {}
    for status, _, _ in rows:
        states[status] = states.get(status, 0) + 1
    done = [(float(lat), float(ts)) for status, lat, ts in rows if status == "COMPLETED"]
    return states, sorted(lat for lat, _ in done), sorted(ts for _, ts in done)


def pct(values, p):
    return values[min(len(values) - 1, int(len(values) * p))] if values else float("nan")


def worker_env():
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    for line in open(f"{WORKER_DIR}/.env.example"):
        if "=" in line and not line.startswith("#"):
            key, value = line.strip().split("=", 1)
            env[key] = value
    for line in open(f"{ROOT}/backend/api/.env"):
        if line.startswith("INTERNAL_API_SECRET="):
            env["INTERNAL_API_SECRET"] = line.strip().split("=", 1)[1]
    return env


def set_workers(count, procs):
    """워커 수를 count 로 맞춘다. stack.sh 가 띄운 워커도 내리고 여기서 직접 관리한다."""
    pid_file = f"{RUN_DIR}/worker.pid"
    if os.path.exists(pid_file):
        try:
            os.kill(int(open(pid_file).read()), signal.SIGTERM)
        except ProcessLookupError:
            pass
        os.remove(pid_file)
    while len(procs) > count:
        proc = procs.pop()
        proc.terminate()
        proc.wait()
    while len(procs) < count:
        port = 8100 + len(procs)
        log = open(f"{RUN_DIR}/loadtest-worker-{port}.log", "a")
        procs.append(subprocess.Popen([f"{WORKER_DIR}/.venv/bin/uvicorn", "main:app", "--port", str(port)],
                                      cwd=WORKER_DIR, env=worker_env(), stdout=log, stderr=log))
    time.sleep(3)


def report_saves(results):
    lat = sorted(r[1] for r in results)
    errors = sum(1 for r in results if r[0] != 200)
    return f"{len(results)} | {errors} | {pct(lat, 0.5) * 1000:.0f}ms | {pct(lat, 0.95) * 1000:.0f}ms | {pct(lat, 0.99) * 1000:.0f}ms | {lat[-1] * 1000:.0f}ms"


def ramp(token, body, pool, procs):
    set_workers(1, procs)
    print("| 유입량 | 요청 | 저장 실패 | 저장 p50 | p95 | p99 | 최대 | 큐 최대 길이 | 완료 p50 | 완료 p95 | 완료 최대 | 유실 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for rate in (1, 2, 5, 10, 20):
        results = fire(token, body, rate, 20, pool)
        ids = [r[2] for r in results if r[2]]
        peak = wait_done(ids)
        states, lat, _ = completion(ids)
        lost = len(ids) - states.get("COMPLETED", 0)
        print(f"| 초당 {rate}건 | {report_saves(results)} | {peak} | {pct(lat, 0.5):.1f}s | {pct(lat, 0.95):.1f}s | {lat[-1]:.1f}s | {lost} |", flush=True)


def scale(token, body, pool, procs):
    backlog = 400
    print("| 워커 수 | 밀린 산책 | 소화 시간 | 처리량 | 1대 대비 |")
    print("|---|---|---|---|---|")
    base = None
    for count in (1, 2, 4):
        set_workers(0, procs)
        results = fire(token, body, 100, backlog / 100, pool)
        ids = [r[2] for r in results if r[2]]
        time.sleep(12)   # 릴레이(10초 주기)가 전부 큐로 발행하기를 기다린다
        ready, _ = queue_depth()
        started = time.time()
        set_workers(count, procs)
        wait_done(ids)
        states, _, done_at = completion(ids)
        elapsed = done_at[-1] - (started + 3)   # set_workers 의 기동 대기 3초를 뺀다
        throughput = len(done_at) / elapsed
        base = base or throughput
        print(f"| {count} | {len(ids)} (큐에 {ready}) | {elapsed:.1f}s | 초당 {throughput:.2f}건 | {throughput / base:.2f}배 |", flush=True)


def outage(token, body, pool, procs):
    set_workers(0, procs)
    results = fire(token, body, 5, 20, pool)
    ids = [r[2] for r in results if r[2]]
    time.sleep(12)
    ready, unacked = queue_depth()
    analyzing = sql(f"SELECT COUNT(*) FROM walking_course WHERE walking_course_id BETWEEN {min(ids)} AND {max(ids)} "
                    "AND analysis_status = 'ANALYZING'")[0][0]
    print(f"워커 0대에서 저장: 요청 | 실패 | p50 | p95 | p99 | 최대 = {report_saves(results)}")
    print(f"워커가 없는 동안 큐에 쌓인 메시지 {ready}, 분석 중 코스 {analyzing}")
    started = time.time()
    set_workers(1, procs)
    wait_done(ids)
    states, _, _ = completion(ids)
    print(f"워커 기동 후 {time.time() - started:.1f}s 에 전부 처리. 상태: {states}, 유실 {len(ids) - states.get('COMPLETED', 0)}")


if __name__ == "__main__":
    procs = []
    try:
        token = login()
        body = walk_body(WALK_SECONDS)
        with ThreadPoolExecutor(64) as pool:
            {"ramp": ramp, "scale": scale, "outage": outage}[sys.argv[1]](token, body, pool, procs)
    finally:
        set_workers(0, procs)
