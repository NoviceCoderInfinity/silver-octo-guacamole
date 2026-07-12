"""Entry point: read /input/tasks.json, caption each video, write /output/results.json."""
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

import config
from gemini_caption import GeminiVideoCaptioner
from llm_client import ClaudeClient, FireworksClient
from pipeline import caption_video

INPUT_PATH = os.environ.get("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/output/results.json")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))


def _run_gemini(task: dict, captioner: GeminiVideoCaptioner) -> dict:
    task_id = task["task_id"]
    styles = task["styles"]
    try:
        captions = captioner.caption_styles(task["video_url"], styles)
    except Exception:
        print(f"[{task_id}] FAILED: {traceback.format_exc()}", file=sys.stderr)
        captions = {s: "" for s in styles}
    return {"task_id": task_id, "captions": captions}


def _build_client():
    assembly = (config.CAPTION_ASSEMBLY or "").strip().lower()
    if assembly == "gemini_direct":
        return None  # handled separately
    if assembly == "qwen_direct":
        if not config.FIREWORKS_API_KEY:
            raise RuntimeError("FIREWORKS_API_KEY required for CAPTION_ASSEMBLY=qwen_direct")
        return FireworksClient(
            config.FIREWORKS_API_KEY,
            config.FIREWORKS_MODEL_ID,
            config.FIREWORKS_BASE_URL,
        )
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY required for Claude caption assemblies")
    return ClaudeClient(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL_ID)


def main() -> int:
    with open(INPUT_PATH, "r") as f:
        tasks = json.load(f)

    assembly = (config.CAPTION_ASSEMBLY or "").strip().lower()
    print(f"[main] assembly={assembly} tasks={len(tasks)} max_workers={MAX_WORKERS}",
          file=sys.stderr)

    if assembly == "gemini_direct":
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY required for CAPTION_ASSEMBLY=gemini_direct")
        captioner = GeminiVideoCaptioner(
            config.GEMINI_API_KEY,
            config.GEMINI_MODEL_ID,
            temperature=config.GEMINI_TEMPERATURE,
        )
        print(f"[main] gemini_model={config.GEMINI_MODEL_ID}", file=sys.stderr)
        workers = max(1, min(MAX_WORKERS, len(tasks)))
        if workers == 1:
            results = [_run_gemini(t, captioner) for t in tasks]
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(lambda t: _run_gemini(t, captioner), tasks))
    else:
        client = _build_client()

        def run_task(task: dict) -> dict:
            task_id = task["task_id"]
            styles = task["styles"]
            try:
                captions = caption_video(task["video_url"], styles, client)
            except Exception:
                print(f"[{task_id}] FAILED: {traceback.format_exc()}", file=sys.stderr)
                captions = {s: "" for s in styles}
            return {"task_id": task_id, "captions": captions}

        workers = max(1, min(MAX_WORKERS, len(tasks)))
        if workers == 1:
            results = [run_task(t) for t in tasks]
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(run_task, tasks))

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
