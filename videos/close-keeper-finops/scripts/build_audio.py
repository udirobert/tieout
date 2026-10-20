#!/usr/bin/env python3
"""Fetch the v2 narration (and optional BGM) from ElevenLabs into assets/.

Reads voice/model/lines from ../audio_request.json and the key from the repo .env.
Prints the measured duration of every clip, because scene timing is derived from the
audio — never from an assumed words-per-second estimate.

    research/.venv/bin/python videos/close-keeper-finops/scripts/build_audio.py
    research/.venv/bin/python videos/close-keeper-finops/scripts/build_audio.py --no-bgm
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJ = Path(__file__).resolve().parent.parent
ROOT = PROJ.parent.parent
REQ = json.loads((PROJ / "audio_request.json").read_text())
OUT = PROJ / "assets" / "voice"
KEY = None


def load_key() -> str:
    import os

    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("ELEVENLABS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
                break
    if not key:
        raise SystemExit("ELEVENLABS_API_KEY not found in the shell environment or .env")
    return key


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def tts(text: str, dest: Path) -> None:
    voice = REQ["voice"]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice['voice_id']}?output_format=mp3_44100_128"
    body = {
        "text": text,
        "model_id": REQ["model_id"],
        "voice_settings": voice["settings"],
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"xi-api-key": load_key(), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        dest.write_bytes(resp.read())


def bgm(prompt: str, length_ms: int, dest: Path) -> None:
    url = "https://api.elevenlabs.io/v1/models/music_v1/generate"
    body = {"prompt": prompt, "force_instrumental": True, "music_length_ms": length_ms}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"xi-api-key": load_key(), "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        dest.write_bytes(resp.read())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0.0
    for line in REQ["lines"]:
        dest = OUT / f"{line['id']}.mp3"
        if dest.exists() and dest.stat().st_size > 2000:
            secs = duration(dest)
            print(f"cached {line['id']} {secs:6.2f}s  {line['beat']}")
        else:
            tts(line["text"], dest)
            secs = duration(dest)
            print(f"vo     {line['id']} {secs:6.2f}s  {line['beat']:12} {dest.name}")
        total += secs
    print(f"\nnarration total: {total:.2f}s across {len(REQ['lines'])} lines")
    print(json.dumps({ln["id"]: round(duration(OUT / f'{ln["id"]}.mp3'), 3) for ln in REQ["lines"]}, indent=2))

    if "--no-bgm" in sys.argv:
        return
    mus = REQ.get("bgm")
    if not mus:
        return
    dest = PROJ / mus["path"]
    try:
        bgm(mus["prompt"], mus["length_ms"], dest)
        print(f"bgm    {duration(dest):6.2f}s  {dest.name}")
    except urllib.error.HTTPError as exc:
        print(f"bgm SKIPPED: HTTP {exc.code} {exc.read().decode()[:220]}")
        print("the film works on narration alone — render without it and decide later")


if __name__ == "__main__":
    main()
