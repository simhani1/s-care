"""동기(2024) 구조와 큐 구조를 같은 CPU 예산의 계산기로 비교한다. 표준 라이브러리만 쓴다.

bench/sync-baseline 브랜치에서 스택을 띄운 뒤 실행한다 (RESULTS.md 의 재현 절차).
  python3 backend/loadtest/bench.py single --arch queue --cpus 0.12 --algo window --minutes 10,20,30,60
  python3 backend/loadtest/bench.py rate   --arch sync  --cpus 0.12 --algo window --rate 0.1 --seconds 120
  python3 backend/loadtest/bench.py burst  --arch queue --cpus 0.28 --algo prefix --n 10 --minutes 30 --workers 2
  python3 backend/loadtest/bench.py fault  --arch sync  --cpus 0.28 --algo window --mode pause --rate 0.3
결과 한 줄을 JSON 으로 backend/.run/bench/results.jsonl 에 덧붙이고 요약을 출력한다.
"""
import argparse
import http.client
import json
import os
import random
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import loadtest
from loadtest import ROOT, login, pct, queue_depth, sql, walk_body

BACKEND = f"{ROOT}/backend"
OUT = f"{BACKEND}/.run/bench"
COMPOSE = ["docker", "compose", "-f", "docker-compose.yml", "-f", "loadtest/compose.bench.yml",
           "--profile", "queue", "--profile", "sync"]
SECRET = loadtest.worker_env()["INTERNAL_API_SECRET"]
ANDROID_READ_TIMEOUT = 10
local = threading.local()


def compose(*args, env=None):
    subprocess.run([*COMPOSE, *args], cwd=BACKEND, check=True, capture_output=True,
                   env=dict(os.environ, **(env or {})))


def get(path, headers, timeout):
    conn = http.client.HTTPConnection("localhost", 8080, timeout=timeout)
    try:
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        return res.status, res.read()
    finally:
        conn.close()


def calculators(arch, count, cpus, algo):
    """계산기를 새로 띄운다. 동기 구조는 시간 초과 뒤에도 계산이 계속 돌기 때문에 매 실행 새로 만든다."""
    loadtest.set_workers(0, [])
    with open(f"{OUT}/calc.log", "a") as log:
        subprocess.run([*COMPOSE, "logs", "--no-log-prefix", "worker"], cwd=BACKEND, stdout=log, stderr=subprocess.DEVNULL)
    compose("rm", "-sf", "worker", "calc", "lb")
    env = {"CALC_CPUS": str(cpus), "STRESS_ALGO": algo, "INTERNAL_API_SECRET": SECRET}
    if arch == "queue":
        compose("up", "-d", "--no-deps", "--scale", f"worker={count}", "worker", env=env)
        deadline = time.time() + 120
        # 관리 API 의 consumers 는 몇 초 늦게 갱신돼 직전 워커가 남아 보인다. 새 워커의 로그로 구독을 확인한다.
        while consumers() != count or subprocess.run([*COMPOSE, "logs", "worker"], cwd=BACKEND, capture_output=True,
                                                     text=True).stdout.count("Listening on request_queue") < count:
            if time.time() > deadline:
                raise RuntimeError("workers did not subscribe")
            time.sleep(1)
    else:
        compose("up", "-d", "--scale", f"calc={count}", "calc", "lb", env=env)
        deadline = time.time() + 120
        while True:
            try:
                conn = http.client.HTTPConnection("localhost", 8000, timeout=5)
                conn.request("GET", "/docs")
                if conn.getresponse().status == 200:
                    break
            except OSError:
                pass
            if time.time() > deadline:
                raise RuntimeError("sync calculator did not start")
            time.sleep(1)


def consumers():
    import base64
    conn = http.client.HTTPConnection("localhost", 15672, timeout=5)
    auth = base64.b64encode(b"scare:scare").decode()
    conn.request("GET", "/api/queues/%2F/request_queue", headers={"Authorization": f"Basic {auth}"})
    return json.loads(conn.getresponse().read()).get("consumers", 0)


def save(token, path, body, t0):
    if not hasattr(local, "conn"):
        local.conn = http.client.HTTPConnection("localhost", 8080, timeout=200)
    sent = time.perf_counter()
    try:
        local.conn.request("POST", path, body=body, headers={"Content-Type": "application/json", "Authorization": token})
        res = local.conn.getresponse()
        data = res.read()
        course_id = json.loads(data)["data"] if res.status == 200 else None
        return {"status": res.status, "lat": time.perf_counter() - sent, "id": course_id, "sent": sent - t0}
    except Exception as e:
        local.conn.close()
        del local.conn
        return {"status": 0, "lat": time.perf_counter() - sent, "id": None, "sent": sent - t0, "err": repr(e)}


class Probes:
    """부하와 무관한 요청(목록 조회)의 지연과, Hikari 커넥션·Tomcat 스레드 사용량을 0.5~1초 간격으로 본다."""

    def __init__(self, token):
        self.token, self.stop, self.pool, self.lists = token, threading.Event(), [], []
        self.executor = ThreadPoolExecutor(64)

    def __enter__(self):
        threading.Thread(target=self.sample_pool, daemon=True).start()
        threading.Thread(target=self.sample_list, daemon=True).start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        self.executor.shutdown(wait=True)

    def sample_pool(self):
        while not self.stop.wait(0.5):
            try:
                self.pool.append(json.loads(get("/internal/bench/pool", {"X-Internal-Secret": SECRET}, 5)[1]))
            except Exception:
                pass

    def one_list(self):
        started = time.perf_counter()
        try:
            status, _ = get("/api/v1/walking/list?page=0&size=10", {"Authorization": self.token}, 120)
        except Exception:
            status = 0
        self.lists.append((status, time.perf_counter() - started))

    def sample_list(self):
        while not self.stop.wait(1):
            self.executor.submit(self.one_list)

    def summary(self):
        lat = sorted(l for _, l in self.lists)
        return {
            "db_active_max": max((p["dbActive"] for p in self.pool), default=None),
            "db_waiting_max": max((p["dbWaiting"] for p in self.pool), default=None),
            "tomcat_busy_max": max((p["tomcatBusy"] - 1 for p in self.pool), default=None),
            "list_n": len(lat), "list_err": sum(1 for s, _ in self.lists if s != 200),
            "list_p50": pct(lat, 0.5), "list_p95": pct(lat, 0.95), "list_max": lat[-1] if lat else None,
        }


def fire(token, path, schedule, actions=()):
    """schedule: 요청을 보낼 시각(초) 목록. 응답이 늦어도 다음 요청을 제때 보낸다(open loop). actions: (시각, 함수)."""
    t0 = time.perf_counter()
    for at, fn in actions:
        threading.Timer(at, fn).start()
    with ThreadPoolExecutor(256) as pool:
        futures = []
        for at, body in schedule:
            delay = t0 + at - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            futures.append(pool.submit(save, token, path, body, t0))
        return [f.result() for f in futures]


def outcomes(arch, results, cap):
    """코스별 결과 유무와 결과가 보이기까지의 시간(저장 요청 시각 기준, 초)."""
    ids = [r["id"] for r in results if r["id"]]
    if not ids:
        return {}, {}
    in_ids = ",".join(map(str, ids))
    waited_until = time.time() + cap
    if arch == "queue":
        while time.time() < waited_until:
            if int(sql(f"SELECT COUNT(*) FROM walking_course WHERE walking_course_id IN ({in_ids}) "
                       "AND analysis_status = 'ANALYZING'")[0][0]) == 0 and sum(queue_depth()) == 0:
                break
            time.sleep(1)
        done = {int(i): float(s) for i, s in sql(
            "SELECT o.walking_course_id, TIMESTAMPDIFF(MICROSECOND, c.created_at, o.updated_at) / 1e6 "
            f"FROM walking_course c JOIN outbox o USING (walking_course_id) WHERE c.walking_course_id IN ({in_ids}) "
            "AND o.status = 'COMPLETED'")}
    else:
        completed = {int(i) for (i,) in sql(f"SELECT walking_course_id FROM walking_course WHERE walking_course_id IN ({in_ids}) "
                                            "AND analysis_status = 'COMPLETED'")}
        done = {r["id"]: r["lat"] for r in results if r["id"] in completed}
    status = {i: ("result" if i in done else "no_result") for i in ids}
    return status, done


def summarize(arch, results, status, done, probes, phases=None):
    lat = sorted(r["lat"] for r in results)
    ok = [r for r in results if r["status"] == 200]
    res_lat = sorted(done.values())
    out = {
        "requests": len(results), "save_ok": len(ok),
        "save_err": {str(s): sum(1 for r in results if r["status"] == s) for s in {r["status"] for r in results} - {200}},
        "save_p50": pct(lat, 0.5), "save_p95": pct(lat, 0.95), "save_p99": pct(lat, 0.99), "save_max": lat[-1],
        "over_android_timeout": sum(1 for l in lat if l > ANDROID_READ_TIMEOUT),
        "with_result": len(done), "saved_without_result": sum(1 for v in status.values() if v == "no_result"),
        "not_saved": len(results) - len(ok),
        "result_p50": pct(res_lat, 0.5), "result_p95": pct(res_lat, 0.95),
        "result_max": res_lat[-1] if res_lat else None,
        **probes.summary(),
    }
    if phases:
        out["phases"] = {}
        for name, lo, hi in phases:
            sel = [r for r in results if lo <= r["sent"] < hi]
            out["phases"][name] = {
                "requests": len(sel), "not_saved": sum(1 for r in sel if r["status"] != 200),
                "with_result": sum(1 for r in sel if r["id"] in done),
                "saved_without_result": sum(1 for r in sel if status.get(r["id"]) == "no_result"),
                "save_max": max((r["lat"] for r in sel), default=None),
            }
    return out


def run(args, schedule, actions=(), phases=None, extra=None):
    path = "/api/v1/walking/sync" if args.arch == "sync" else "/api/v1/walking"
    calculators(args.arch, args.workers, args.cpus, args.algo)
    if args.arch == "queue":
        deadline = time.time() + 30
        while sum(queue_depth()) and time.time() < deadline:
            time.sleep(1)
        assert sum(queue_depth()) == 0, "request_queue not empty"
    token = login()
    started = time.time()
    with Probes(token) as probes:
        results = fire(token, path, schedule, actions)
        status, done = outcomes(args.arch, results, args.cap)
        time.sleep(1)
    out = {"scenario": args.scenario, "arch": args.arch, "cpus": args.cpus, "algo": args.algo,
           "workers": args.workers, "started": started, "ended": time.time(), **(extra or {}), **summarize(args.arch, results, status, done, probes, phases)}
    if args.arch == "queue":
        logs = subprocess.run([*COMPOSE, "logs", "--no-log-prefix", "worker"], cwd=BACKEND, capture_output=True, text=True).stdout
        calc = [float(l.rsplit(" in ", 1)[1].rstrip("s")) for l in logs.splitlines() if " calculated " in l]
        out["calc_n"], out["calc_mean"] = len(calc), sum(calc) / len(calc) if calc else None
    os.makedirs(OUT, exist_ok=True)
    with open(f"{OUT}/results.jsonl", "a") as f:
        f.write(json.dumps(out) + "\n")
    print(json.dumps(out, ensure_ascii=False), flush=True)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenario", choices=["single", "rate", "burst", "fault"])
    p.add_argument("--arch", choices=["sync", "queue"], required=True)
    p.add_argument("--cpus", type=float, required=True)
    p.add_argument("--algo", choices=["window", "prefix"], required=True)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--minutes", default="30")
    p.add_argument("--rate", type=float, default=0.1)
    p.add_argument("--seconds", type=float, default=120)
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--mode", choices=["pause", "stop"], default="pause")
    p.add_argument("--cap", type=float, default=1800, help="큐 구조에서 결과를 기다리는 최대 시간(초)")
    p.add_argument("--label", default="")
    args = p.parse_args()
    extra = {"label": args.label}
    if args.scenario == "single":
        for m in map(int, args.minutes.split(",")):
            run(args, [(random.uniform(0, 10), walk_body(m * 60))], extra={**extra, "minutes": m})
    elif args.scenario == "rate":
        m = int(args.minutes)
        body = walk_body(m * 60)
        run(args, [(i / args.rate, body) for i in range(int(args.rate * args.seconds))],
            extra={**extra, "minutes": m, "rate": args.rate, "seconds": args.seconds})
    elif args.scenario == "burst":
        m = int(args.minutes)
        body = walk_body(m * 60)
        run(args, [(0, body)] * args.n, extra={**extra, "minutes": m, "n": args.n})
    else:
        m = int(args.minutes)
        body = walk_body(m * 60)
        service = "worker" if args.arch == "queue" else "calc"
        down, up = ("pause", "unpause") if args.mode == "pause" else ("stop", "start")
        actions = [(30, lambda: compose(down, service)), (120, lambda: compose(up, service))]
        run(args, [(i / args.rate, body) for i in range(int(args.rate * 180))], actions,
            phases=[("before", 0, 30), ("during", 30, 120), ("after", 120, 1e9)],
            extra={**extra, "minutes": m, "rate": args.rate, "mode": args.mode})


if __name__ == "__main__":
    main()
