#!/usr/bin/env python3
"""Build caption_groups.json + compositions/captions.html from audio_meta.json."""
import json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
meta = json.loads((ROOT / "audio_meta.json").read_text())

# Match index.html scene voice starts
VO_START = {
    0: 0.0,
    1: 7.458,
    2: 15.751,
    3: 27.62,
    4: 32.198,
    5: 40.584,
    6: 45.255,
}
TOTAL = 48.904
SUPPRESS_AT = 45.255  # frame 6 — logo read on screen

groups = []
gid_box = [0]
for v in sorted(meta["voices"], key=lambda x: x["frame"]):
    off = VO_START[v["frame"]]
    words = [
        {**w, "start": round(w["start"] + off, 3), "end": round(w["end"] + off, 3)}
        for w in v["words"]
    ]
    words = [w for w in words if w["start"] < SUPPRESS_AT]
    cur = []

    def flush(frame=v["frame"], _cur=cur):
        if not _cur:
            return
        g = gid_box[0]
        groups.append({
            "id": f"caption-group-{g}",
            "frame": frame,
            "start": _cur[0]["start"],
            "end": _cur[-1]["end"],
            "text": " ".join(w["text"] for w in _cur),
            "words": [
                {
                    "id": f"caption-word-{g}-{i}",
                    "text": w["text"],
                    "start": w["start"],
                    "end": w["end"],
                }
                for i, w in enumerate(_cur)
            ],
        })
        gid_box[0] += 1
        _cur.clear()

    for i, w in enumerate(words):
        cur.append(w)
        ends_punct = bool(re.search(r"[.,?!:;—]$", w["text"]))
        gap = words[i + 1]["start"] - w["end"] if i + 1 < len(words) else 99
        if len(cur) >= 3 or (ends_punct and len(cur) >= 2) or gap > 0.38:
            flush()
    flush()

(ROOT / "caption_groups.json").write_text(
    json.dumps({"total_duration_s": TOTAL, "width": 1920, "height": 1080, "groups": groups}, indent=1)
)
print(f"wrote caption_groups.json ({len(groups)} groups)")

SKIN = """<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style data-brand-tokens="">
  :root {
    --cap-ink: #1a1a1a;
    --cap-canvas: #fffaf3;
    --cap-accent: #2d8a4e;
    --cap-accent-2: #e07a3a;
    --font-display: "IBM Plex Sans", system-ui, sans-serif;
    --font-body: "IBM Plex Sans", system-ui, sans-serif;
    --cap-band-top: 880px;
    --cap-band-height: 160px;
  }
</style>
<style>
  @import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600;700&display=swap");
  #captions-root { position: absolute; inset: 0; pointer-events: none; }
  .caption-layer { position: absolute; inset: 0; z-index: 30; pointer-events: none; }
  .caption-stage {
    position: absolute; left: 0; right: 0;
    top: var(--cap-band-top, 880px);
    height: var(--cap-band-height, 160px);
    display: flex; align-items: center; justify-content: center;
  }
  .caption-group {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    opacity: 0;
  }
  .caption-pill {
    max-width: 72%;
    padding: 16px 36px 18px;
    background: var(--cap-canvas);
    border: 2px solid rgba(26,26,26,0.14);
    border-radius: 8px;
    box-shadow: 6px 8px 0 rgba(26,26,26,0.08);
  }
  .caption-line {
    display: flex; flex-wrap: wrap; justify-content: center;
    gap: 0.1em 0.28em;
    font-family: var(--font-display);
    font-weight: 600;
    font-size: clamp(28px, 2.4vw, 38px);
    line-height: 1.22;
    letter-spacing: -0.02em;
  }
  .caption-word {
    display: inline-block;
    padding: 0 0.02em 0.05em;
    color: color-mix(in srgb, var(--cap-ink) 42%, var(--cap-canvas));
    border-bottom: 3px solid transparent;
  }
  .caption-word.is-active {
    color: var(--cap-ink);
    border-bottom: 3px solid var(--cap-accent);
  }
  .caption-word.is-spoken {
    color: var(--cap-ink);
    border-bottom: 3px solid transparent;
  }
  .caption-word.cap-brand { color: var(--cap-accent); font-weight: 700; }
  .caption-word.cap-num { font-family: "IBM Plex Mono", monospace; font-weight: 700; }
</style>
<div id="captions-root" data-composition-id="captions" data-start="0" data-duration="__DURATION__" data-width="1920" data-height="1080">
  <div class="caption-layer" aria-hidden="true">
    <div id="caption-stage" class="caption-stage"></div>
  </div>
</div>
<script>
  var GROUPS = __GROUPS__;
  var DURATION = __DURATION__;
  (function () {
    var stage = document.getElementById("caption-stage");
    GROUPS.forEach(function (group, g) {
      var groupEl = document.createElement("div");
      groupEl.className = "caption-group";
      groupEl.id = "caption-group-" + g;
      var pill = document.createElement("div");
      pill.className = "caption-pill";
      var line = document.createElement("div");
      line.className = "caption-line";
      (group.words || []).forEach(function (w, i) {
        var span = document.createElement("span");
        span.className = "caption-word";
        span.id = "caption-word-" + g + "-" + i;
        span.textContent = String(w.text);
        line.appendChild(span);
      });
      pill.appendChild(line);
      groupEl.appendChild(pill);
      stage.appendChild(groupEl);
    });
    window.__timelines = window.__timelines || {};
    var tl = gsap.timeline({ paused: true });
    GROUPS.forEach(function (group, g) {
      var groupEl = document.getElementById("caption-group-" + g);
      var words = group.words || [];
      var next = GROUPS[g + 1];
      var isLast = g === GROUPS.length - 1;
      var start = Math.max(0, Number(group.start));
      var end = isLast ? DURATION : Math.min(Number(next.start), Number(group.end) + 0.28);
      if (end <= start) end = start + 0.01;
      tl.set(groupEl, { opacity: 1 }, start);
      tl.set(groupEl, { opacity: 0 }, end);
      words.forEach(function (w, i) {
        var el = document.getElementById("caption-word-" + g + "-" + i);
        var at = Math.max(start, Number(w.start));
        tl.set(el, { className: "caption-word" }, start);
        tl.set(el, { className: "caption-word is-active" }, at);
        tl.fromTo(el, { scale: 0.98 }, { scale: 1, duration: 0.14, ease: "power1.out" }, at);
        if (i + 1 < words.length) {
          var nextAt = Math.max(start, Number(words[i + 1].start));
          tl.set(el, { className: "caption-word is-spoken" }, nextAt);
        }
      });
      if (words.length) {
        var lastEl = document.getElementById("caption-word-" + g + "-" + (words.length - 1));
        var lastSpoken = Math.min(end, Number(words[words.length - 1].end) + 0.08);
        tl.set(lastEl, { className: "caption-word is-spoken" }, lastSpoken);
      }
    });
    tl.set("#captions-root", { opacity: 0 }, __SUPPRESS__);
    tl.to({}, { duration: DURATION }, 0);
    window.__timelines["captions"] = tl;
  })();
</script>"""

html = (
    "<template>\n"
    + SKIN.replace("__GROUPS__", json.dumps(groups))
    .replace("__DURATION__", str(TOTAL))
    .replace("__SUPPRESS__", str(SUPPRESS_AT))
    + "\n</template>\n"
)
(ROOT / "compositions" / "captions.html").write_text(html)
print("wrote compositions/captions.html")
