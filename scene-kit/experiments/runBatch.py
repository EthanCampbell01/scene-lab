from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from typing import Any, Dict, List

from metrics import compute_metrics, count_invalid_targets

INPUT_COST_PER_MILLION = 5.0      # USD per 1M input tokens
OUTPUT_COST_PER_MILLION = 15.0    # USD per 1M output tokens

def estimate_tokens(text: str) -> int:
    # Rough estimate: 1 token ≈ 4 characters
    return int(len(text) / 4)


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
    here = os.path.dirname(os.path.abspath(__file__))          # .../scene-kit/experiments
    scene_kit_dir = os.path.abspath(os.path.join(here, ".."))  # .../scene-kit

    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="ollama", choices=["ollama", "openrouter"])
    ap.add_argument("--briefs", default=os.path.join(here, "briefs.json"))
    ap.add_argument("--runsPerBrief", type=int, default=5)
    ap.add_argument("--workflow", default="robust", choices=["robust"])
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--outDir", default=os.path.join(here, "output", "runs"))
    args = ap.parse_args()

    briefs: List[Dict[str, Any]] = _read_json(args.briefs)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_root = os.path.join(args.outDir, stamp)
    os.makedirs(run_root, exist_ok=True)

    summary_csv = os.path.join(run_root, "summary.csv")
    header = [
    "timestamp", "provider", "workflow", "briefId", "variantId", "run",
    "ok", "returncode", "outPath",

    "modelRuntimeSeconds",
    "estimatedCostUSD",
    "estimatedInputTokens",
    "estimatedOutputTokens",

    "nodeCount", "endingCount", "choicesTotal",
    "invalidChoiceTargetsPreNormalize", "invalidChoiceTargetsPostNormalize",
    "reachableNodesCount", "reachableEndingsCount",

    "maxDepth", "terminalNodeRatio", "uniqueTargetRatio",
    "avgNarrationWords", "lexicalDiversity", "effectsTotal", "endingTypeDiversity",

    "structuralScore", "branchScore", "narrativeScore", "totalScore",
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

            start_time = time.time()

            proc = subprocess.run(
            cmd,
            cwd=os.path.dirname(__file__) + "/..",
            capture_output=True,
               text=True
            )

            end_time = time.time()
            runtime_seconds = round(end_time - start_time, 3)


            # Save console output for evidence
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write("### STDOUT ###\n")
                f.write(proc.stdout or "")
                f.write("\n\n### STDERR ###\n")
                f.write(proc.stderr or "")

            scene_exists = os.path.exists(out_path)
            ok = scene_exists  # IMPORTANT: trust artifact existence more than return code

            row: Dict[str, Any] = {
                "timestamp": stamp,
                "provider": args.provider,
                "workflow": args.workflow,
                "briefId": brief_id,
                "variantId": variant_id,
                "run": i,
                "ok": ok,
                "returncode": proc.returncode,
                "outPath": out_path,
                "modelRuntimeSeconds": runtime_seconds,
            }

            if ok:
                try:
                    
                    scene = _read_json(out_path)

                    # COST ESTIMATION
                    prompt_tokens = estimate_tokens(brief_text)

                    with open(out_path, "r", encoding="utf-8") as f:
                        output_text = f.read()

                    output_tokens = estimate_tokens(output_text)

                    input_cost = (prompt_tokens / 1_000_000) * INPUT_COST_PER_MILLION
                    output_cost = (output_tokens / 1_000_000) * OUTPUT_COST_PER_MILLION
                    estimated_cost = round(input_cost + output_cost, 6)

                    row["estimatedCostUSD"] = estimated_cost
                    row["estimatedInputTokens"] = prompt_tokens
                    row["estimatedOutputTokens"] = output_tokens

                    invalid_pre = count_invalid_targets(scene)
                    invalid_post = count_invalid_targets(scene)  # pipeline may already normalize

                    m = compute_metrics(
                        scene,
                        invalid_targets_pre=invalid_pre,
                        invalid_targets_post=invalid_post,
                    )

                    _write_json(metrics_path, m)

                    row.update(m)

                except Exception as e:
                    # Scene file exists but we couldn't parse/measure it
                    _write_json(metrics_path, {"error": "metrics_failed", "message": str(e)})
                    row.update({
                        "ok": False,
                        "nodeCount": "",
                        "endingCount": "",
                        "invalidChoiceTargets": "",
                        "reachableNodesCount": "",
                        "reachableEndingsCount": "",
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


    #  RANKING STEP


    import csv
    from collections import defaultdict
    from statistics import mean, pstdev

    if os.path.exists(summary_csv):

        with open(summary_csv, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        # ---- Rank individual runs ----
        ok_rows = [r for r in rows if str(r.get("ok", "")).lower() == "true"]

        def to_float(x):
            try:
                return float(x)
            except:
                return 0.0

        ok_rows.sort(key=lambda r: to_float(r.get("totalScore")), reverse=True)

        ranked_path = os.path.join(run_root, "ranked_runs.csv")
        with open(ranked_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for r in ok_rows:
                writer.writerow(r)

        # ---- Brief-level summary ----
        buckets = defaultdict(list)
        for r in rows:
            buckets[r.get("briefId", "unknown")].append(r)

        briefs_summary_path = os.path.join(run_root, "briefs_summary.csv")

        with open(briefs_summary_path, "w", encoding="utf-8", newline="") as f:
            fieldnames = [
                "briefId", "runs", "okRuns",
                "successRate",
                "meanTotalScore",
                "stdTotalScore",
                "bestTotalScore"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for brief_id, rs in buckets.items():
                total = len(rs)
                oks = [r for r in rs if str(r.get("ok", "")).lower() == "true"]
                scores = [to_float(r.get("totalScore")) for r in oks]

                writer.writerow({
                    "briefId": brief_id,
                    "runs": total,
                    "okRuns": len(oks),
                    "successRate": round(len(oks)/total, 4) if total else 0.0,
                    "meanTotalScore": round(mean(scores), 3) if scores else "",
                    "stdTotalScore": round(pstdev(scores), 3) if len(scores) >= 2 else "",
                    "bestTotalScore": round(max(scores), 3) if scores else "",
                })

        print(f"Auto-ranking complete.")
        print(f"Ranked runs: {ranked_path}")
        print(f"Brief summary: {briefs_summary_path}")


    print(f"Done. Results in: {run_root}")
    print(f"Summary CSV: {summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
