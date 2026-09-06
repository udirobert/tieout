#!/usr/bin/env python3
"""Recompute index.html scene timings (tight Twitter pace)."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / "audio_meta.json").read_text())
PAD = 0.12
MIN_DUR = {4: 4.8, 5: 4.5, 6: 2.5}

voices = sorted(meta["voices"], key=lambda v: v["frame"])
starts = []
durs = []
t = 0.0
vo_starts = {}
for v in voices:
    vo_starts[v["frame"]] = round(t, 3)
    d = v["duration_s"] + PAD
    d = max(d, MIN_DUR.get(v["frame"], d))
    d = round(d, 3)
    starts.append(t)
    durs.append(d)
    t += d

total = round(t, 3)
print("Scene timings:", list(zip(starts, durs)), "total", total)

idx = (ROOT / "index.html").read_text()
slots = [
    ("slot-00", "frame-00-skyline", starts[0], durs[0], "vo-00", vo_starts[0], voices[0]["duration_s"]),
    ("slot-01", "frame-01-proof", starts[1], durs[1], "vo-01", vo_starts[1], voices[1]["duration_s"]),
    ("slot-02", "frame-02-hack", starts[2], durs[2], "vo-02", vo_starts[2], voices[2]["duration_s"]),
    ("slot-03", "frame-03-results", starts[3], durs[3], "vo-03", vo_starts[3], voices[3]["duration_s"]),
    ("slot-04", "frame-04-unlock", starts[4], durs[4], "vo-04", vo_starts[4], voices[4]["duration_s"]),
    ("slot-05", "frame-05-ship", starts[5], durs[5], "vo-05", vo_starts[5], voices[5]["duration_s"]),
    ("slot-06", "frame-06-end", starts[6], durs[6], "vo-06", vo_starts[6], voices[6]["duration_s"]),
]

for slot, _, st, du, vo, vst, vdu in slots:
    idx = re.sub(
        rf'(<div id="{slot}"[^>]*data-start=")[^"]+(" data-duration=")[^"]+',
        rf'\g<1>{st}\g<2>{du}',
        idx,
        count=1,
    )
    idx = re.sub(
        rf'(<audio id="{vo}"[^>]*data-start=")[^"]+(" data-duration=")[^"]+',
        rf'\g<1>{vst}\g<2>{vdu}',
        idx,
        count=1,
    )

idx = re.sub(r'data-duration="43\.935"', f'data-duration="{total}"', idx)
idx = re.sub(
    r'tl\.to\(\{\}, \{ duration: [0-9.]+\ }, 0\);',
    f'tl.to({{}}, {{ duration: {total} }}, 0);',
    idx,
)
# faster whips + transition times
whip_times = [starts[i] for i in range(1, 7)]
old_whips = ["6.487", "13.021", "20.623", "27.435", "33.935", "40.435"]
for old, new in zip(old_whips, whip_times):
    idx = idx.replace(old, str(new))
idx = idx.replace("duration: 0.28", "duration: 0.16").replace("duration: 0.32", "duration: 0.18")
idx = idx.replace('data-volume="0.11"', 'data-volume="0.15"')
(ROOT / "index.html").write_text(idx)

# patch build_captions VO_START
bc = (ROOT / "scripts" / "build_captions.py").read_text()
bc = re.sub(
    r"VO_START = \{[^}]+\}",
    "VO_START = " + json.dumps({str(k): v for k, v in vo_starts.items()}, indent=2).replace('"', '"').replace("\n  ", "\n    "),
    bc,
    count=1,
)
# simpler: replace the dict block manually
vo_block = "VO_START = {\n" + "\n".join(
    f"    {k}: {vo_starts[k]}," for k in sorted(vo_starts)
) + "\n}"
bc = re.sub(r"VO_START = \{.*?\n\}", vo_block, bc, flags=re.S)
bc = re.sub(r"TOTAL = [0-9.]+", f"TOTAL = {total}", bc)
bc = re.sub(r"SUPPRESS_AT = [0-9.]+", f"SUPPRESS_AT = {vo_starts[6]}", bc)
(ROOT / "scripts" / "build_captions.py").write_text(bc)
print("updated index.html + build_captions.py")
