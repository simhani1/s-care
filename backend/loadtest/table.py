"""bench.py 결과(results.jsonl)를 마크다운 표로 찍는다. 사용: python3 table.py [results.jsonl] [scenario]"""
import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "backend/.run/bench/results.jsonl"
only = sys.argv[2] if len(sys.argv) > 2 else None
COLS = ["scenario", "label", "arch", "cpus", "algo", "workers", "minutes", "n", "rate", "mode", "requests", "save_ok",
        "save_err", "save_p50", "save_p99", "save_max", "over_android_timeout", "with_result", "saved_without_result",
        "not_saved", "result_p50", "result_p95", "result_max", "db_active_max", "db_waiting_max", "tomcat_busy_max",
        "list_err", "list_p95", "list_max", "calc_mean"]


def fmt(v):
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, dict):
        return " ".join(f"{k}:{x}" for k, x in v.items()) or "-"
    return "-" if v in (None, "") else str(v)


rows = [json.loads(l) for l in open(path) if l.strip()]
rows = [r for r in rows if not only or r["scenario"] == only]
print("| " + " | ".join(COLS) + " |")
print("|" + "---|" * len(COLS))
for r in rows:
    print("| " + " | ".join(fmt(r.get(c)) for c in COLS) + " |")
    if r.get("phases"):
        for name, p in r["phases"].items():
            print(f"|   {name} | " + " ".join(f"{k}={fmt(v)}" for k, v in p.items()) + " |")
