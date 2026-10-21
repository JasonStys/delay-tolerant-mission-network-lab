"""Deterministic native/reference contracts and descriptive timing by Jason Stys.

Function: main. Variables: reviewed cases, default result ids, timings and traced allocation peak.
Only --write updates contracts; no machine-dependent performance threshold. Index: docs/CODE_INDEX.md.
"""

import argparse
import statistics
import time
import tracemalloc
from pathlib import Path

from dtnlab.engine import SCENARIOS, Settings, build_run, canonical


def main() -> None:
    """Verify native+reference outputs and print bounded-workload runtime/allocation observations."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rows = []
    for scenario in SCENARIOS:
        run = build_run(Settings(scenario))
        rows.append(
            {
                "scenario": scenario,
                "id": run["id"],
                "totals": run["totals"],
                "recovery": run["recovery"],
            }
        )
    body = canonical({"cases": rows})
    path = Path("docs/reports/benchmark.json")
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
    elif path.read_bytes() != body:
        raise SystemExit("Native/reference evidence drift; investigate before updating contracts")
    times = []
    tracemalloc.start()
    for _ in range(20):
        start = time.perf_counter()
        build_run(Settings("restart-inflight"))
        times.append((time.perf_counter() - start) * 1000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    print(
        f"Nine deterministic native/reference contracts passed; median {statistics.median(times):.3f} ms, Python traced peak {peak} bytes (includes tracing/IPC; not Rust/OS RSS)"
    )


if __name__ == "__main__":
    main()
