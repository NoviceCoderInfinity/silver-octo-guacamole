"""Entry point: read /input/tasks.json, caption each video, write /output/results.json."""
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

import config
from llm_client import ClaudeClient, FireworksClient
from minimax_direct import caption_video_minimax
from pipeline import caption_video

INPUT_PATH = os.environ.get("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/output/results.json")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "5"))


def _build_client():
    assembly = (config.CAPTION_ASSEMBLY or "").strip().lower()
    if assembly in ("minimax_direct", "qwen_direct"):
        if not config.FIREWORKS_API_KEY:
            raise RuntimeError("FIREWORKS_API_KEY required for Fireworks assemblies")
        # Qwen fallback / qwen_direct uses qwen3p7-plus; primary minimax model is separate.
        model = (
            config.FIREWORKS_MODEL_ID
            if assembly == "minimax_direct"
            else "accounts/fireworks/models/qwen3p7-plus"
        )
        return FireworksClient(config.FIREWORKS_API_KEY, model, config.FIREWORKS_BASE_URL)
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY required for Claude caption assemblies")
    return ClaudeClient(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL_ID)


def main() -> int:
    with open(INPUT_PATH, "r") as f:
        tasks = json.load(f)

    assembly = (config.CAPTION_ASSEMBLY or "").strip().lower()
    print(
        f"[main] assembly={assembly} tasks={len(tasks)} max_workers={MAX_WORKERS} "
        f"model={config.FIREWORKS_MODEL_ID} frames={config.MIN_FRAMES}-{config.MAX_FRAMES}"
        f"@{config.FRAME_MAX_WIDTH}",
        file=sys.stderr,
    )

    def run_task(task: dict) -> dict:
        task_id = task["task_id"]
        styles = task["styles"]
        try:
            if assembly == "minimax_direct":
                captions = caption_video_minimax(task["video_url"], styles)
            else:
                client = _build_client()
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

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
