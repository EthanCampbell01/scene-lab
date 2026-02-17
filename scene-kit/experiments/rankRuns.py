from __future__ import annotations

import argparse
import csv
import os
from collections import defaultdict
from statistics import mean, pstdev
from typing import Any, Dict, List


def _read_rows(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(path: str, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _to_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runDir", required=True, help="Path to a single timestamp run folder containing summary.csv")
    args = ap.parse_args()

    summary_path = os.path.join(args.runDir, "summary.csv")
    if not os.path.exists(summary_path):
        raise SystemExit(f"Could not find summary.csv at: {summary_path}")

    rows = _read_rows(summary_path)

    # Ranked runs (only ok=True)
    ok_rows = [r for r in rows if str(r.get("ok", "")).lower() == "true"]
    ok_rows.sort(key=lambda r: _to_float(r.get("totalScore", 0)), reverse=True)

    ranked_path = os.path.join(args.runDir, "ranked_runs.csv")
    _write_rows(ranked_path, list(rows[0].keys()) if rows else [], ok_rows)

    # Per-brief summary
    buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        bid = r.get("briefId", "unknown")
        buckets[bid].append(r)

    brief_rows: List[Dict[str, Any]] = []
    for brief_id, rs in sorted(buckets.items()):
        total = len(rs)
        oks = [r for r in rs if str(r.get("ok", "")).lower() == "true"]
        success_rate = (len(oks) / total) if total else 0.0

        scores = [_to_float(r.get("totalScore", 0)) for r in oks]
        brief_rows.append({
            "briefId": brief_id,
            "runs": total,
            "okRuns": len(oks),
            "successRate": round(success_rate, 4),
            "meanTotalScore": round(mean(scores), 3) if scores else "",
            "stdTotalScore": round(pstdev(scores), 3) if len(scores) >= 2 else "",
            "bestTotalScore": round(max(scores), 3) if scores else "",
        })

    briefs_path = os.path.join(args.runDir, "briefs_summary.csv")
    _write_rows(
        briefs_path,
        ["briefId", "runs", "okRuns", "successRate", "meanTotalScore", "stdTotalScore", "bestTotalScore"],
        brief_rows
    )

    print(f"Wrote: {ranked_path}")
    print(f"Wrote: {briefs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
