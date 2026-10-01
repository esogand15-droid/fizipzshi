#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Transcribe one lecture video with faster-whisper (Persian).

Runs on a GitHub Actions runner: the agent sandbox cannot reach huggingface.co
nor does it have the CPU budget. Designed for *resumable* execution: audio is
split into chunks, each chunk is transcribed and pushed to the branch
immediately, so a job timeout never loses completed work.

usage:
  transcribe_one.py <slug> <video_path> [--model large-v3] [--chunk-min 20]
                    [--offset-min 0] [--limit-min 0]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

OUT_DIR = Path("work/transcripts")


def sh(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


def run_relay(msg: str) -> None:
    subprocess.run(["bash", "tools/relay_push.sh", msg], check=False)


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def extract_audio(video: Path, wav: Path, start: float | None = None, dur: float | None = None) -> None:
    # an earlier relay push can drop the (git-ignored) tmp dir mid-run; recreate it here
    wav.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if start:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(video)]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav)]
    sh(cmd)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("video")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--chunk-min", type=float, default=20.0)
    ap.add_argument("--offset-min", type=float, default=0.0)
    ap.add_argument("--limit-min", type=float, default=0.0)
    args = ap.parse_args()

    slug = args.slug
    video = Path(args.video)
    outdir = OUT_DIR / slug
    outdir.mkdir(parents=True, exist_ok=True)
    tmp = Path("work/tmp_media")
    tmp.mkdir(parents=True, exist_ok=True)

    total = audio_duration(video)
    start0 = args.offset_min * 60
    span = (args.limit_min * 60) if args.limit_min else max(0.0, total - start0)
    end = min(total, start0 + span)
    chunk = args.chunk_min * 60

    meta = {
        "slug": slug, "video": str(video), "duration": total,
        "offset": start0, "end": end, "model": args.model, "chunk_min": args.chunk_min,
    }
    (outdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    t = start0
    plan = []
    while t < end - 5:
        d = min(chunk, end - t)
        idx = int(t // chunk)          # absolute chunk index -> stable across parts
        plan.append((idx, t, d))
        t += d

    # skip chunks already done (resume support)
    todo = [(i, s, d) for (i, s, d) in plan if not (outdir / f"chunk_{i:03d}.json").exists()]
    print(f"[{slug}] duration={total/60:.1f}min chunks={len(plan)} todo={len(todo)}", flush=True)
    if not todo:
        merge(outdir)
        run_relay(f"transcribe-{slug}-complete(noop)")
        return 0

    from faster_whisper import WhisperModel  # imported late: heavy

    t0 = time.time()
    model = WhisperModel(args.model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
    print(f"[{slug}] model loaded in {time.time()-t0:.0f}s", flush=True)

    for (i, s, d) in todo:
        wav = tmp / f"{slug}_{i:03d}.wav"
        if not wav.exists():
            extract_audio(video, wav, s, d)
        ct0 = time.time()
        segments, info = model.transcribe(
            str(wav), language="fa", beam_size=5, vad_filter=True,
            condition_on_previous_text=False, temperature=[0.0, 0.2, 0.4],
            initial_prompt="درس فیزیک پزشکی، پرتو، رادیوبیولوژی، MRI، سونوگرافی، دزیمتری.",
        )
        rows = []
        for sg in segments:
            rows.append({
                "start": round(sg.start + s, 2),
                "end": round(sg.end + s, 2),
                "text": sg.text.strip(),
            })
        payload = {"slug": slug, "chunk": i, "chunk_start": s, "chunk_end": s + d,
                   "duration_sec": d, "elapsed_sec": round(time.time() - ct0, 1),
                   "language": info.language, "lang_prob": round(info.language_probability, 3),
                   "segments": rows}
        (outdir / f"chunk_{i:03d}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{slug}] chunk {i} done in {(time.time()-ct0)/60:.1f}min "
              f"({d/60:.1f}min audio, x{(time.time()-ct0)/d:.2f} realtime)", flush=True)
        wav.unlink(missing_ok=True)
        run_relay(f"transcribe-{slug}-chunk{i:03d}")

    merge(outdir)
    run_relay(f"transcribe-{slug}-complete")
    return 0


def merge(outdir: Path) -> None:
    chunks = sorted(outdir.glob("chunk_*.json"))
    if not chunks:
        return
    segs: list[dict] = []
    for c in chunks:
        segs += json.loads(c.read_text(encoding="utf-8"))["segments"]
    segs.sort(key=lambda r: r["start"])
    (outdir / "raw.json").write_text(json.dumps(segs, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = []
    for r in segs:
        m, s = divmod(int(r["start"]), 60)
        lines.append(f"[{m:02d}:{s:02d}] {r['text']}")
    (outdir / "raw.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"merged {len(segs)} segments -> {outdir/'raw.json'}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
