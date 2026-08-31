"""Closed-loop load driver for /v1/predict.

usage: python scripts/loadtest.py HOST PORT REQUESTS CONCURRENCY
"""
import http.client
import json
import statistics
import sys
import threading
import time
from pathlib import Path

PAYLOAD = Path("payloads/sample.json").read_bytes()
HEADERS = {"content-type": "application/json"}


def run(host: str, port: int, requests: int, concurrency: int) -> dict:
    per_worker = requests // concurrency
    latencies: list[float] = []
    codes: dict[int, int] = {}
    lock = threading.Lock()

    def worker() -> None:
        conn = http.client.HTTPConnection(host, port, timeout=10)
        local: list[float] = []
        local_codes: dict[int, int] = {}
        for _ in range(per_worker):
            started = time.perf_counter()
            conn.request("POST", "/v1/predict", PAYLOAD, HEADERS)
            response = conn.getresponse()
            response.read()
            local.append((time.perf_counter() - started) * 1000)
            local_codes[response.status] = local_codes.get(response.status, 0) + 1
        conn.close()
        with lock:
            latencies.extend(local)
            for status, count in local_codes.items():
                codes[status] = codes.get(status, 0) + count

    threads = [threading.Thread(target=worker) for _ in range(concurrency)]
    started = time.perf_counter()
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    wall = time.perf_counter() - started

    latencies.sort()
    return {
        "requests": len(latencies),
        "concurrency": concurrency,
        "codes": codes,
        "rps": round(len(latencies) / wall, 1),
        "p50_ms": round(statistics.median(latencies), 2),
        "p95_ms": round(latencies[int(len(latencies) * 0.95) - 1], 2),
        "p99_ms": round(latencies[int(len(latencies) * 0.99) - 1], 2),
        "max_ms": round(latencies[-1], 2),
    }


if __name__ == "__main__":
    host, port, requests, concurrency = sys.argv[1:5]
    print(json.dumps(run(host, int(port), int(requests), int(concurrency))))
