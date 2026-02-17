from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from typing import Any, Dict, List

from metrics import compute_metrics, count_invalid_targets






def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _append_csv(path: str, header: List[str], row: Dict[str, Any]) -> None:
    exists = os.path.exists(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        if not exists:
            f.write(",".join(header) + "\n")
        f.write(",".join(str(row.get(h, "")) for h in header) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="ollama", choices=["ollama", "openrouter"])
    ap.add_argument("--briefs", default="briefs.json")
    ap.add_argument("--runsPerBrief", type=int, default=5)
    ap.add_argument("--workflow", default="robust", choices=["robust"])  # we’ll add baseline/twoPass next
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--outDir", default=os.path.join("output", "runs"))
    args = ap.parse_args()

    briefs: List[Dict[str, Any]] = _read_json(args.briefs)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_root = os.path.join(args.outDir, stamp)
    os.makedirs(run_root, exist_ok=True)

    summary_csv = os.path.join(run_root, "summary.csv")
    header = [
        "timestamp", "provider", "workflow", "briefId", "variantId", "run",
        "ok", "outPath",
        "nodeCount", "endingCount", "invalidChoiceTargets",
        "reachableNodesCount", "reachableEndingsCount",
    ]

    for b in briefs:
        brief_id = b["briefId"]
        variant_id = b.get("variantId", "default")
        brief_text = b["brief"]

        for i in range(1, args.runsPerBrief + 1):
            run_dir = os.path.join(run_root, brief_id, args.workflow, f"run{i:03d}")
            os.makedirs(run_dir, exist_ok=True)

            out_path = os.path.abspath(os.path.join(run_dir, "scene.json"))
            raw_path = os.path.abspath(os.path.join(run_dir, "raw.txt"))
            metrics_path = os.path.abspath(os.path.join(run_dir, "metrics.json"))


            cmd = [
                "python", "pipeline.py",
                "--provider", args.provider,
                "--variant", variant_id,
                "--brief", brief_text,
                "--timeout", str(args.timeout),
                "--retries", str(args.retries),
                "--out", out_path,
            ]

            # Capture stdout/stderr for evidence
            proc = subprocess.run(cmd, cwd=os.path.dirname(__file__) + "/..",
                                  capture_output=True, text=True)

            # Save the console output as “raw evidence” (not the model raw yet)
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write("### STDOUT ###\n")
                f.write(proc.stdout or "")
                f.write("\n\n### STDERR ###\n")
                f.write(proc.stderr or "")

            ok = proc.returncode == 0 and os.path.exists(out_path)

            row: Dict[str, Any] = {
                "timestamp": stamp,
                "provider": args.provider,
                "workflow": args.workflow,
                "briefId": brief_id,
                "variantId": variant_id,
                "run": i,
                "ok": ok,
                "outPath": out_path,
            }

            if ok:
                scene = _read_json(out_path)

        # Pre-normalize invalid targets (note: if your pipeline already normalizes
        # before writing, this will match post for now — still useful to log)
        invalid_pre = count_invalid_targets(scene)
        invalid_post = count_invalid_targets(scene)

        m = compute_metrics(
            scene,
            invalid_targets_pre=invalid_pre,
            invalid_targets_post=invalid_post,
        )

        _write_json(metrics_path, m)

        # Map your metrics keys to the CSV header keys you chose
        row.update({
            "nodeCount": m.get("nodeCount", ""),
            "endingCount": m.get("endingCount", ""),
            "invalidChoiceTargets": invalid_post,  # keep this column meaningful
            "reachableNodesCount": m.get("reachableNodesCount", ""),
            "reachableEndingsCount": m.get("reachableEndingsCount", ""),
        })

    else:
            _write_json(metrics_path, {"error": "pipeline_failed", "returncode": proc.returncode})
            row.update({
                    "nodeCount": "",
                    "endingCount": "",
                    "invalidChoiceTargets": "",
                    "reachableNodesCount": "",
                    "reachableEndingsCount": "",
                })

            _append_csv(summary_csv, header, row)

    print(f"Done. Results in: {run_root}")
    print(f"Summary CSV: {summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
