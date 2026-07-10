#!/usr/bin/env python3
"""Run novel arms vs Arush baseline with an independent (non-Claude) judge.

Foolproofing rules:
  - Generator is primarily Claude Sonnet → judge MUST NOT be Claude.
  - Default judge: Fireworks Qwen (third family vs Claude + Gemini used in some arms).
  - Same task set, same frame width for baseline-comparable arms, shared video cache.
  - Empty captions score 1/1; failed tasks recorded.

Usage:
  .venv/bin/python -m exp_arms.run_suite
  EXP_MAX_TASKS=3 .venv/bin/python -m exp_arms.run_suite   # smoke
  EXP_ARMS=verifiability,scene_frames .venv/bin/python -m exp_arms.run_suite
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config
from exp_arms.arms import ARMS
from exp_arms.media import cached_video_path, uniform_frames_b64
from llm_client import FireworksClient
from pipeline import build_critique_prompt, build_critique_schema
from video_utils import frame_to_b64  # noqa: F401

OUT_DIR = ROOT / "sample_output" / "exp_novel_v1"
INPUT_PATH = Path(os.environ.get(
    "INPUT_PATH", str(ROOT / "eval_input" / "tasks_gcs12.json"),
))
MAX_WORKERS = int(os.environ.get("EXP_MAX_WORKERS", "2"))


def _judge_client() -> FireworksClient:
    if not config.FIREWORKS_API_KEY:
        raise RuntimeError("FIREWORKS_API_KEY required for independent judge")
    # Force Fireworks even if .env says anthropic — bias rule.
    model = os.environ.get(
        "EXP_JUDGE_MODEL_ID",
        config.FIREWORKS_MODEL_ID or "accounts/fireworks/models/qwen3p7-plus",
    )
    print(f"[judge] provider=fireworks model={model} (Claude forbidden for this suite)",
          flush=True)
    return FireworksClient(config.FIREWORKS_API_KEY, model, config.FIREWORKS_BASE_URL)


def generate_arm(arm_id: str, tasks: list) -> list:
    meta = ARMS[arm_id]
    fn = meta["fn"]
    print(f"\n=== GENERATE {arm_id}: {meta['title']} ===", flush=True)
    t0 = time.time()
    results = []

    def one(task):
        tid = task["task_id"]
        try:
            caps = fn(task["video_url"], task["styles"])
        except Exception:
            print(f"[{arm_id}/{tid}] FAIL: {traceback.format_exc()}", file=sys.stderr)
            caps = {s: "" for s in task["styles"]}
        empty = [s for s, c in caps.items() if not c.strip()]
        if empty:
            print(f"[{arm_id}/{tid}] empty styles: {empty}", file=sys.stderr)
        return {"task_id": tid, "captions": caps}

    with ThreadPoolExecutor(max_workers=max(1, min(MAX_WORKERS, len(tasks)))) as pool:
        futs = {pool.submit(one, t): t["task_id"] for t in tasks}
        done = {}
        for fut in as_completed(futs):
            row = fut.result()
            done[row["task_id"]] = row
            print(f"[{arm_id}] {row['task_id']} done", flush=True)
    results = [done[t["task_id"]] for t in tasks]
    print(f"[{arm_id}] wall={time.time()-t0:.1f}s", flush=True)
    return results


def judge_results(tasks_by_id: dict, results: list, client: FireworksClient) -> dict:
    def one(result):
        task = tasks_by_id[result["task_id"]]
        styles = task["styles"]
        captions = result["captions"]
        path = str(cached_video_path(task["video_url"]))
        frames = uniform_frames_b64(
            path,
            max_width=768,
            seconds_per_frame=config.SECONDS_PER_FRAME,
            min_frames=config.MIN_FRAMES,
            max_frames=config.MAX_FRAMES,
        )
        try:
            scores = client.generate_json(
                build_critique_prompt(captions, styles, len(frames)),
                build_critique_schema(styles),
                frames_b64=frames,
                max_tokens=3072,
            )
        except Exception:
            print(f"[judge/{result['task_id']}] FAIL: {traceback.format_exc()}",
                  file=sys.stderr)
            scores = {
                s: {"accuracy": 1, "tone_fit": 1, "notes": "judge_failed"}
                for s in styles
            }
        return {"task_id": result["task_id"], "scores": scores}

    with ThreadPoolExecutor(max_workers=max(1, min(MAX_WORKERS, len(results)))) as pool:
        judged = list(pool.map(one, results))

    acc = tone = n = 0
    per_style = {}
    for row in judged:
        for style, sc in row["scores"].items():
            a = int(sc.get("accuracy", 0))
            t = int(sc.get("tone_fit", 0))
            acc += a
            tone += t
            n += 1
            bucket = per_style.setdefault(style, {"acc": 0, "tone": 0, "n": 0})
            bucket["acc"] += a
            bucket["tone"] += t
            bucket["n"] += 1
    summary = {
        "num_scores": n,
        "avg_accuracy": round(acc / n, 4) if n else 0.0,
        "avg_tone_fit": round(tone / n, 4) if n else 0.0,
        "combined_01": round(((acc + tone) / (2 * n)) / 5.0, 4) if n else 0.0,
        "per_style": {
            s: {
                "avg_accuracy": round(v["acc"] / v["n"], 4),
                "avg_tone_fit": round(v["tone"] / v["n"], 4),
            }
            for s, v in per_style.items()
        },
    }
    return {"summary": summary, "results": judged}


def main() -> int:
    with open(INPUT_PATH) as f:
        tasks = json.load(f)
    max_tasks = int(os.environ.get("EXP_MAX_TASKS", "0") or 0)
    if max_tasks > 0:
        tasks = tasks[:max_tasks]
    tasks_by_id = {t["task_id"]: t for t in tasks}

    arm_filter = os.environ.get("EXP_ARMS", "").strip()
    if arm_filter:
        arm_ids = [a.strip() for a in arm_filter.split(",") if a.strip()]
    else:
        arm_ids = list(ARMS.keys())
    for a in arm_ids:
        if a not in ARMS:
            raise SystemExit(f"unknown arm {a}; choose from {list(ARMS)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    judge = _judge_client()

    scoreboard = {
        "judge": "fireworks/" + (os.environ.get("EXP_JUDGE_MODEL_ID") or config.FIREWORKS_MODEL_ID),
        "n_tasks": len(tasks),
        "input": str(INPUT_PATH),
        "bias_rule": "Judge is Fireworks; generators are Claude (+Gemini assist on some arms). Never Claude-judging-Claude.",
        "arms": {},
    }

    baseline_combined = None
    for arm_id in arm_ids:
        results = generate_arm(arm_id, tasks)
        (OUT_DIR / f"results_{arm_id}.json").write_text(json.dumps(results, indent=2))
        print(f"\n=== JUDGE {arm_id} ===", flush=True)
        judged = judge_results(tasks_by_id, results, judge)
        (OUT_DIR / f"judged_{arm_id}.json").write_text(json.dumps(judged, indent=2))
        summary = judged["summary"]
        entry = {
            "title": ARMS[arm_id]["title"],
            "novel": ARMS[arm_id]["novel"],
            **summary,
        }
        if arm_id == "arush_baseline":
            baseline_combined = summary["combined_01"]
            entry["delta_vs_arush"] = 0.0
        elif baseline_combined is not None:
            entry["delta_vs_arush"] = round(summary["combined_01"] - baseline_combined, 4)
        scoreboard["arms"][arm_id] = entry
        (OUT_DIR / "scoreboard.json").write_text(json.dumps(scoreboard, indent=2))
        print(json.dumps(entry, indent=2), flush=True)

    # Rank novel arms by combined, then by delta
    ranked = sorted(
        ((k, v) for k, v in scoreboard["arms"].items() if v.get("novel")),
        key=lambda kv: (kv[1]["combined_01"], kv[1].get("delta_vs_arush", 0)),
        reverse=True,
    )
    scoreboard["ranking_novel"] = [
        {"arm": k, "combined_01": v["combined_01"], "delta_vs_arush": v.get("delta_vs_arush")}
        for k, v in ranked
    ]
    (OUT_DIR / "scoreboard.json").write_text(json.dumps(scoreboard, indent=2))
    print("\n===== SCOREBOARD =====")
    print(json.dumps(scoreboard, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
