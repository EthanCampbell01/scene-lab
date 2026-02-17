from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from critic import evaluate_narrative

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

def _append_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


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
    critic_report_path = os.path.join(run_root, "critic_report.txt")

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
    "criticScore",
    "dialogueQuality",
    "emotionalCoherence",
    "characterConsistency",
    "dramaticTension",
    "overallNarrativeQuality",
    "compositeScore",
    "criticJsonPath",

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
                    critic = evaluate_narrative(scene)

                    # save critic per-run too
                    critic_path = os.path.join(run_dir, "critic.json")
                    _write_json(critic_path, critic)

                    _append_text(
                    critic_report_path,
                    (
                        "\n" + "=" * 90 + "\n"
                        f"briefId: {brief_id}\n"
                        f"variantId: {variant_id}\n"
                        f"run: {i}\n"
                        f"scenePath: {out_path}\n"
                        f"criticScore: {critic.get('criticScore','')}\n"
                        f"dialogueQuality: {critic.get('dialogueQuality','')} | "
                        f"emotionalCoherence: {critic.get('emotionalCoherence','')} | "
                        f"characterConsistency: {critic.get('characterConsistency','')} | "
                        f"dramaticTension: {critic.get('dramaticTension','')} | "
                        f"originalityAndVoice: {critic.get('originalityAndVoice','')} | "
                        f"overallNarrativeQuality: {critic.get('overallNarrativeQuality','')}\n"
                        f"keyIssues: {critic.get('keyIssues','')}\n"
                        f"standoutLine: {critic.get('standoutLine','')}\n"
                        f"worstLine: {critic.get('worstLine','')}\n"
                        f"justification: {critic.get('justification','')}\n"
                    ),
                )

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

                    critic = evaluate_narrative(scene)

                    critic_path = os.path.join(run_dir, "critic.json")
                    _write_json(critic_path, critic)

                    row.update({
                        "criticScore": critic.get("criticScore", ""),
                        "dialogueQuality": critic.get("dialogueQuality", ""),
                        "emotionalCoherence": critic.get("emotionalCoherence", ""),
                        "characterConsistency": critic.get("characterConsistency", ""),
                        "dramaticTension": critic.get("dramaticTension", ""),
                        "overallNarrativeQuality": critic.get("overallNarrativeQuality", ""),
                        "criticJsonPath": critic_path,
                    })

                    # Composite: 40% structure + 60% narrative quality
                    struct_score_100 = (float(row.get("totalScore", 0) or 0) / 24.0) * 100.0
                    critic_score_100 = (float(row.get("criticScore", 0) or 0) / 50.0) * 100.0

                    row["compositeScore"] = round(0.4 * struct_score_100 + 0.6 * critic_score_100, 2)



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

    import glob

    report_path = os.path.join(run_root, "critics_report.txt")

    def fnum(x, default=0.0):
        try:
            return float(x)
        except:
            return default

    entries = []

    # Find every critic.json created in this run
    for critic_file in glob.glob(os.path.join(run_root, "**", "critic.json"), recursive=True):
        run_dir = os.path.dirname(critic_file)
        scene_path = os.path.join(run_dir, "scene.json")
        metrics_path = os.path.join(run_dir, "metrics.json")

        try:
            with open(critic_file, "r", encoding="utf-8") as f:
                critic = json.load(f)
        except:
            continue

        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                metrics = json.load(f)
        except:
            metrics = {}

        # compositeScore is in summary.csv row, but metrics.json may also contain totals.
        # If you didn’t store compositeScore in metrics, we’ll approximate from critic + structural totalScore.
        structural = fnum(metrics.get("totalScore", 0.0))
        critic_score = fnum(critic.get("criticScore", 0.0))
        composite = round(0.4 * (structural / 24.0 * 100.0) + 0.6 * (critic_score / 50.0 * 100.0), 2)

        entries.append({
            "run_dir": run_dir,
            "scene_path": scene_path,
            "sceneId": metrics.get("sceneId", ""),
            "variantId": metrics.get("variantId", ""),
            "criticScore": critic_score,
            "compositeScore": composite,
            "critic": critic,
            "metrics": metrics,
        })

    entries.sort(key=lambda e: e["compositeScore"], reverse=True)

    with open(report_path, "w", encoding="utf-8") as out:
        out.write(f"CRITIC REPORT (ranked) — {stamp}\n")
        out.write("=" * 80 + "\n\n")

        for idx, e in enumerate(entries, start=1):
            c = e["critic"]
            out.write(f"#{idx}  composite={e['compositeScore']}  critic={e['criticScore']}/50\n")
            out.write(f"sceneId: {e['sceneId']}\n")
            out.write(f"variant: {e['variantId']}\n")
            out.write(f"path: {e['run_dir']}\n")

            out.write(
                "scores: "
                f"dialogue={c.get('dialogueQuality')}  "
                f"emotion={c.get('emotionalCoherence')}  "
                f"character={c.get('characterConsistency')}  "
                f"tension={c.get('dramaticTension')}  "
                f"overall={c.get('overallNarrativeQuality')}\n"
            )

            key_issues = c.get("keyIssues", [])
            if isinstance(key_issues, list) and key_issues:
                out.write("keyIssues:\n")
                for it in key_issues[:3]:
                    out.write(f" - {it}\n")

            sl = c.get("standoutLine", "")
            if sl:
                out.write(f"standoutLine: {sl}\n")

            just = c.get("justification", "")
            if just:
                out.write(f"justification: {just}\n")

            out.write("\n" + "-" * 80 + "\n\n")

    print(f"Wrote critic report: {report_path}")



if __name__ == "__main__":
    raise SystemExit(main())
