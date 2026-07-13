"""Entry point: read /input/tasks.json, caption each video, write /output/results.json."""
import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor

import config
from llm_client import ClaudeClient, FireworksClient
from pipeline import caption_video

INPUT_PATH = os.environ.get("INPUT_PATH", "/input/tasks.json")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/output/results.json")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))


def _build_qwen():
    if not config.FIREWORKS_API_KEY:
        raise RuntimeError("FIREWORKS_API_KEY required")
    return FireworksClient(
        config.FIREWORKS_API_KEY,
        config.FIREWORKS_MODEL_ID,
        config.FIREWORKS_BASE_URL,
    )


def _build_claude():
    if not config.ANTHROPIC_API_KEY:
        return None
    return ClaudeClient(config.ANTHROPIC_API_KEY, config.CLAUDE_MODEL_ID)


def main() -> int:
    with open(INPUT_PATH, "r") as f:
        tasks = json.load(f)

    qwen = _build_qwen()
    claude = _build_claude()
    print(
        f"[main] assembly=qwen_direct workers={MAX_WORKERS} frames="
        f"{config.MIN_FRAMES}@{config.FRAME_MAX_WIDTH} claude_fill={bool(claude)}",
        file=sys.stderr,
    )

    def run_task(task: dict) -> dict:
        task_id = task["task_id"]
        styles = task["styles"]
        captions = {s: "" for s in styles}
        try:
            # Temporarily force qwen path via client; assembly from config.
            captions = caption_video(task["video_url"], styles, qwen)
        except Exception:
            print(f"[{task_id}] qwen FAILED: {traceback.format_exc()}", file=sys.stderr)

        missing = [s for s in styles if len(str(captions.get(s, "")).split()) < 6]
        if missing and claude is not None:
            try:
                # Full Claude single_shot pass as last resort for the clip.
                import os as _os
                prev = _os.environ.get("CAPTION_ASSEMBLY")
                _os.environ["CAPTION_ASSEMBLY"] = "single_shot"
                # Reload assembly from env in caption_video via config already loaded —
                # call specialists by constructing a one-off: use caption_video with
                # patched config attribute.
                old = config.CAPTION_ASSEMBLY
                config.CAPTION_ASSEMBLY = "single_shot"
                filled = caption_video(task["video_url"], missing, claude)
                config.CAPTION_ASSEMBLY = old
                if prev is None:
                    _os.environ.pop("CAPTION_ASSEMBLY", None)
                else:
                    _os.environ["CAPTION_ASSEMBLY"] = prev
                for s in missing:
                    if len(str(filled.get(s, "")).split()) >= 6:
                        captions[s] = filled[s]
                        print(f"[{task_id}] claude rescued {s}", file=sys.stderr)
            except Exception:
                print(f"[{task_id}] claude rescue FAILED: {traceback.format_exc()}",
                      file=sys.stderr)

        return {"task_id": task_id, "captions": {s: captions.get(s, "") for s in styles}}

    workers = max(1, min(MAX_WORKERS, len(tasks)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(run_task, tasks))

    # Final assert log
    empties = sum(
        1 for r in results for s, c in r["captions"].items() if len(str(c).split()) < 6
    )
    print(f"[main] short_or_empty_cells={empties}", file=sys.stderr)

    os.makedirs(os.path.dirname(OUTPUT_PATH) or ".", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(results, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
