"""Shared media helpers for novel-arm experiments (download cache + frame variants)."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

from video_utils import (
    choose_num_frames,
    download_video,
    extract_frames,
    frame_to_b64,
    get_duration_seconds,
)

CACHE_DIR = Path(os.environ.get(
    "EXP_VIDEO_CACHE",
    str(Path(__file__).resolve().parent.parent / ".cache" / "videos"),
))


def cached_video_path(video_url: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(video_url.encode()).hexdigest()[:16]
    dest = CACHE_DIR / f"{digest}.mp4"
    if not dest.exists() or dest.stat().st_size == 0:
        download_video(video_url, str(dest))
    return dest


def uniform_frames_b64(video_path: str, max_width: int, seconds_per_frame: float,
                       min_frames: int, max_frames: int) -> list[str]:
    duration = get_duration_seconds(video_path)
    n = choose_num_frames(duration, seconds_per_frame, min_frames, max_frames)
    frames_dir = str(Path(video_path).with_suffix("")) + "_frames_uniform"
    os.makedirs(frames_dir, exist_ok=True)
    # Reuse if already extracted at this width/count.
    existing = sorted(
        os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.startswith("frame_")
    )
    if len(existing) != n:
        for p in existing:
            os.remove(p)
        existing = extract_frames(video_path, frames_dir, num_frames=n, max_width=max_width)
    return [frame_to_b64(p) for p in existing]


def scene_aware_frames_b64(video_path: str, max_width: int, seconds_per_frame: float,
                           min_frames: int, max_frames: int,
                           scene_threshold: float = 0.30) -> list[str]:
    """Mix scene-change peaks with uniform samples for temporal coverage.

    Novel vs Arush: Arush is purely uniform. Scene cuts often carry the action the
    judge notices; uniform-only can miss them between ticks.
    """
    duration = max(get_duration_seconds(video_path), 1.0)
    target = choose_num_frames(duration, seconds_per_frame, min_frames, max_frames)
    frames_dir = str(Path(video_path).with_suffix("")) + "_frames_scene"
    os.makedirs(frames_dir, exist_ok=True)
    scene_pat = os.path.join(frames_dir, "scene_%03d.jpg")

    # Extract scene-change frames (may be fewer or more than target).
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", (
                f"select='gt(scene\\,{scene_threshold})',"
                f"scale='min({max_width}\\,iw)':-2"
            ),
            "-vsync", "vfr",
            "-q:v", "3",
            scene_pat,
        ],
        capture_output=True, check=False,
    )
    scene_paths = sorted(
        os.path.join(frames_dir, f) for f in os.listdir(frames_dir) if f.startswith("scene_")
    )

    # Always include uniform coverage so static clips still get enough evidence.
    uni_dir = os.path.join(frames_dir, "uniform")
    os.makedirs(uni_dir, exist_ok=True)
    uni_paths = extract_frames(video_path, uni_dir, num_frames=target, max_width=max_width)

    # Interleave: take up to half from scene peaks (by file mtime/order), fill from uniform.
    half = max(1, target // 2)
    picked = scene_paths[:half]
    for p in uni_paths:
        if len(picked) >= target:
            break
        picked.append(p)
    # Dedup by basename content size+name roughly via path uniqueness already.
    picked = picked[:target]
    while len(picked) < target and uni_paths:
        # pad with uniform if scene extract failed entirely
        for p in uni_paths:
            if p not in picked:
                picked.append(p)
            if len(picked) >= target:
                break
        break
    return [frame_to_b64(p) for p in picked[:target]]
