#!/usr/bin/env python3
"""fal.ai image-to-video generator.

One-shot CLI: submit → poll → download. Reads FAL_KEY from env (Hermes
autoloads ~/.hermes/.env, so no manual sourcing needed). Plain
`python3 generate.py ...` invocations don't match any Hermes
DANGEROUS_PATTERNS, so this skips the dangerous-command approval path
entirely.

Usage:
    python3 generate.py \\
        --image https://example.com/photo.jpg \\
        --prompt "slow zoom in, cinematic lighting" \\
        [--quality low|high] \\
        [--duration 5] \\
        [--audio] \\
        [--output ./out.mp4] \\
        [--poll-interval 5] \\
        [--timeout 600]

Defaults: quality=low (Veo 3.1 Lite), duration=4s, audio off, output=./video_<id>.mp4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

MODELS = {
    "low":  "fal-ai/veo3.1/lite/image-to-video",
    "high": "fal-ai/kling-video/v3/standard/image-to-video",
}

QUEUE_BASE = "https://queue.fal.run"


def _http(method: str, url: str, key: str, body: dict | None = None,
          timeout: int = 60) -> dict:
    """Minimal JSON HTTP via stdlib. No external deps."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Key {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        raise SystemExit(f"HTTP {e.code} {e.reason}: {body_text}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Network error: {e.reason}") from e
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise SystemExit(f"Non-JSON response: {raw[:500]}")


def _build_payload(quality: str, image_url: str, prompt: str,
                   duration: int, audio: bool) -> dict:
    if quality == "low":
        return {
            "image_url": image_url,
            "prompt": prompt,
            "aspect_ratio": "auto",
            "duration": f"{duration}s",
            "resolution": "480p",
            "generate_audio": audio,
            "safety_tolerance": "4",
        }
    return {
        "image_url": image_url,
        "prompt": prompt,
        "duration": duration,
        "audio": audio,
    }


def _resolve_output_path(arg_output: str | None, request_id: str,
                         video_url: str) -> Path:
    if arg_output:
        p = Path(arg_output).expanduser().resolve()
        if p.suffix == "":
            p = p / f"video_{request_id}.mp4"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    # Default: cwd, derive extension from URL
    parsed = urllib.parse.urlparse(video_url)
    ext = Path(parsed.path).suffix or ".mp4"
    return Path.cwd() / f"video_{request_id}{ext}"


def _download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=300) as resp, \
            dest.open("wb") as fh:
        while chunk := resp.read(1 << 16):
            fh.write(chunk)


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="fal-video-generate",
        description="Generate a video from an image via fal.ai (Veo Lite / Kling v3).",
    )
    ap.add_argument("--image", required=True, help="Public URL of the source image.")
    ap.add_argument("--prompt", required=True, help="Motion / animation prompt.")
    ap.add_argument("--quality", choices=("low", "high"), default="low",
                    help="low=Veo 3.1 Lite (default, cheap), high=Kling v3 standard.")
    ap.add_argument("--duration", type=int, default=4,
                    help="Video duration in seconds (default 4).")
    ap.add_argument("--audio", action="store_true",
                    help="Enable audio generation (off by default to save cost).")
    ap.add_argument("--output", help="Output file path or directory.")
    ap.add_argument("--poll-interval", type=int, default=5,
                    help="Status poll interval in seconds (default 5).")
    ap.add_argument("--timeout", type=int, default=600,
                    help="Total timeout for completion in seconds (default 600).")
    ap.add_argument("--no-download", action="store_true",
                    help="Print result JSON only; don't download the video.")
    ap.add_argument("--quiet", action="store_true", help="Suppress progress logs.")
    args = ap.parse_args()

    key = os.environ.get("FAL_KEY")
    if not key:
        print("ERROR: FAL_KEY not set in environment.", file=sys.stderr)
        print("Hermes autoloads ~/.hermes/.env; verify FAL_KEY is set there.",
              file=sys.stderr)
        return 2

    model = MODELS[args.quality]
    submit_url = f"{QUEUE_BASE}/{model}"
    payload = _build_payload(args.quality, args.image, args.prompt,
                             args.duration, args.audio)

    def log(msg: str) -> None:
        if not args.quiet:
            print(msg, file=sys.stderr, flush=True)

    log(f"[submit] {model}")
    submit_resp = _http("POST", submit_url, key, payload)
    request_id = submit_resp.get("request_id")
    if not request_id:
        print(f"ERROR: no request_id in submit response: {submit_resp}",
              file=sys.stderr)
        return 1
    log(f"[queued] request_id={request_id}")

    # Status URLs from response when present (more robust to model changes).
    status_url = submit_resp.get("status_url") or \
        f"{QUEUE_BASE}/{model}/requests/{request_id}/status"
    result_url = submit_resp.get("response_url") or \
        f"{QUEUE_BASE}/{model}/requests/{request_id}"

    deadline = time.time() + args.timeout
    last_status = ""
    while True:
        if time.time() > deadline:
            print(f"ERROR: timeout after {args.timeout}s "
                  f"(request_id={request_id}, last status={last_status})",
                  file=sys.stderr)
            return 3
        st = _http("GET", status_url, key)
        status = st.get("status", "")
        if status != last_status:
            log(f"[status] {status}")
            last_status = status
        if status == "COMPLETED":
            break
        if status in ("FAILED", "CANCELLED", "ERROR"):
            print(f"ERROR: job {status}: {st}", file=sys.stderr)
            return 4
        time.sleep(args.poll_interval)

    result = _http("GET", result_url, key)
    video = result.get("video") or {}
    video_url = video.get("url")
    if not video_url:
        print(json.dumps(result, indent=2))
        print("ERROR: completed but no video.url in result.", file=sys.stderr)
        return 5

    if args.no_download:
        print(json.dumps({
            "request_id": request_id,
            "video_url": video_url,
            "result": result,
        }, indent=2))
        return 0

    dest = _resolve_output_path(args.output, request_id, video_url)
    log(f"[download] {video_url} -> {dest}")
    _download(video_url, dest)
    print(json.dumps({
        "request_id": request_id,
        "video_url": video_url,
        "saved_to": str(dest),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
