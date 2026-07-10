#!/usr/bin/env python3
"""A/B: Arush lean 0.87 baseline vs this repo's Gemini-describe hybrid.

Runs each generator in its own subprocess (clean imports), then scores both with
the same Claude judge from THIS repo. Never writes to Arush's git remotes.

Usage:
    .venv/bin/python ab_vs_arush.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARUSH_ROOT = Path(os.environ.get(
    "ARUSH_BASELINE_ROOT",
    "/Users/anupam/Code/himawari-friend-main",
))
OUT_DIR = ROOT / "sample_output" / "ab_gemini_vs_arush"
INPUT_PATH = Path(os.environ.get("INPUT_PATH", str(ROOT / "sample_input" / "tasks.json")))
VENV_PY = ROOT / ".venv" / "bin" / "python"


def run_generator(label: str, cwd: Path, env_extra: dict, out_path: Path) -> None:
    env = os.environ.copy()
    # Prefer this repo's .env values for keys; generators load_dotenv from their cwd.
    env.update(env_extra)
    env["INPUT_PATH"] = str(INPUT_PATH)
    env["OUTPUT_PATH"] = str(out_path)
    env["MAX_WORKERS"] = env.get("MAX_WORKERS", "2")
    print(f"\n=== generating: {label} ===", flush=True)
    t0 = time.time()
    # Use our venv interpreter so both arms share installed deps; Arush code is pure
    # Python and only needs anthropic/dotenv/requests/ffmpeg.
    cmd = [str(VENV_PY), "main.py"]
    proc = subprocess.run(
        cmd, cwd=str(cwd), env=env, capture_output=True, text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    if proc.returncode != 0:
        raise RuntimeError(f"{label} failed with exit {proc.returncode}")
    print(f"[{label}] wall={time.time()-t0:.1f}s -> {out_path}", flush=True)


def judge_arm(tasks_by_id: dict, results: list, client, config, pipeline, video_utils) -> dict:
    def one(result):
        task = tasks_by_id[result["task_id"]]
        styles = task["styles"]
        captions = result["captions"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = os.path.join(tmp_dir, "clip.mp4")
            video_utils.download_video(task["video_url"], video_path)
            duration = video_utils.get_duration_seconds(video_path)
            n = video_utils.choose_num_frames(
                duration, config.SECONDS_PER_FRAME, config.MIN_FRAMES, config.MAX_FRAMES,
            )
            frames_dir = os.path.join(tmp_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)
            paths = video_utils.extract_frames(
                video_path, frames_dir, num_frames=n, max_width=config.FRAME_MAX_WIDTH,
            )
            frames_b64 = [video_utils.frame_to_b64(p) for p in paths]
            scores = client.generate_json(
                pipeline.build_critique_prompt(captions, styles, len(frames_b64)),
                pipeline.build_critique_schema(styles),
                frames_b64=frames_b64,
                max_tokens=3072,
            )
        return {"task_id": result["task_id"], "scores": scores}

    with ThreadPoolExecutor(max_workers=min(3, len(results))) as pool:
        judged = list(pool.map(one, results))

    acc = tone = n = 0
    for row in judged:
        for sc in row["scores"].values():
            acc += int(sc.get("accuracy", 0))
            tone += int(sc.get("tone_fit", 0))
            n += 1
    summary = {
        "num_scores": n,
        "avg_accuracy": round(acc / n, 4) if n else 0.0,
        "avg_tone_fit": round(tone / n, 4) if n else 0.0,
        "combined_01": round(((acc + tone) / (2 * n)) / 5.0, 4) if n else 0.0,
    }
    return {"summary": summary, "results": judged}


def main() -> int:
    if not VENV_PY.is_file():
        print("Missing .venv — create it first", file=sys.stderr)
        return 1
    if not ARUSH_ROOT.is_dir():
        print(f"Arush baseline root missing: {ARUSH_ROOT}", file=sys.stderr)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    arush_out = OUT_DIR / "results_arush.json"
    gem_out = OUT_DIR / "results_gemini.json"

    # Shared keys from THIS repo's environment / .env (loaded by child via dotenv).
    # Point Arush cwd at friend tree but inject keys so it doesn't need its own .env.
    from dotenv import dotenv_values
    vals = {k: v for k, v in dotenv_values(ROOT / ".env").items() if v}

    # Arm A: Arush lean pipeline (no Gemini, no critique — whatever is on friend main).
    run_generator(
        "arush_baseline_0.87",
        ARUSH_ROOT,
        {
            **vals,
            # Ensure Arush does not accidentally pick up Gemini describe (it has none).
            "DESCRIBE_BACKEND": "claude",
            "ENABLE_CRITIQUE_REPAIR": "false",
        },
        arush_out,
    )

    # Arm B: our hybrid — Gemini full-video describe, Claude styles, critique OFF.
    run_generator(
        "gemini_describe_hybrid",
        ROOT,
        {
            **vals,
            "DESCRIBE_BACKEND": "gemini",
            "ENABLE_CRITIQUE_REPAIR": "false",
            "GEMINI_MODEL_ID": vals.get("GEMINI_MODEL_ID", "gemini-2.5-flash"),
        },
        gem_out,
    )

    # Judge both with this repo's Claude judge.
    sys.path.insert(0, str(ROOT))
    import config
    import pipeline
    import video_utils
    from llm_client import ClaudeJudgeClient

    with open(INPUT_PATH) as f:
        tasks = {t["task_id"]: t for t in json.load(f)}
    arush_results = json.loads(arush_out.read_text())
    gem_results = json.loads(gem_out.read_text())

    print("\n=== judging both arms (same Claude judge) ===", flush=True)
    judge = ClaudeJudgeClient(config.ANTHROPIC_API_KEY, config.JUDGE_MODEL_ID)
    judged_arush = judge_arm(tasks, arush_results, judge, config, pipeline, video_utils)
    judged_gem = judge_arm(tasks, gem_results, judge, config, pipeline, video_utils)
    (OUT_DIR / "judged_arush.json").write_text(json.dumps(judged_arush, indent=2))
    (OUT_DIR / "judged_gemini.json").write_text(json.dumps(judged_gem, indent=2))

    summary = {
        "arush_baseline": judged_arush["summary"],
        "gemini_hybrid": judged_gem["summary"],
        "delta_combined": round(
            judged_gem["summary"]["combined_01"] - judged_arush["summary"]["combined_01"], 4,
        ),
        "notes": (
            "Local Claude-judge on 3 sample clips only — not the hidden leaderboard. "
            "Gemini arm isolates DESCRIBE_BACKEND=gemini with critique/repair OFF."
        ),
    }
    (OUT_DIR / "comparison.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
