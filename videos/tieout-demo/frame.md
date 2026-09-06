---
version: alpha
name: tieout — Dither Editorial (video / frame layer)
description: >
  Light paper world for tieout hackathon demo. Locked dither plate, IBM Plex type,
  one hero device: the benchmark receipt (physical slip carrying WML → tieout stats).
  Motion grammar from yaler-trailer + fondof: structure before props, objects land on beat,
  kicker spine, whip transitions.
unit: the frame — 1920×1080
principle: atoms are sacred · composition is free · numbers come from the script

colors:
  paper: "#f5f0e8"
  paper-raised: "#fffaf3"
  paper-inset: "#e8e0d4"
  ink: "#1a1a1a"
  ink-muted: "#6b6560"
  grey: "#b8b0a4"
  orange: "#c45a1a"
  orange-voltage: "#e07a3a"
  green: "#267643"
  green-hero: "#2d8a4e"
  bloom: "rgba(45,138,78,0.25)"

typography:
  display: { fontFamily: "IBM Plex Sans", weight: 700, tracking: "-0.03em" }
  stat: { fontFamily: "IBM Plex Mono", weight: 700, tracking: "-0.04em" }
  kicker: { fontFamily: "IBM Plex Mono", weight: 500, tracking: "0.14em", upper: true, size: "26px" }
  caption: { fontFamily: "IBM Plex Sans", weight: 400, size: "28px", color: "ink-muted" }
  ticket: { fontFamily: "IBM Plex Mono", weight: 500, tracking: "0.12em", upper: true }

spacing:
  slide-pad: "6%"
  rule: "2px"

components:
  dither-plate:
    backgroundColor: "{colors.paper}"
    texture: "ordered dither dots 5px, phase-shift ambient"
    description: "Full-bleed locked ground on every frame. Never camera-travel."
  kicker-spine:
    typography: "{typography.kicker}"
    rule: "{spacing.rule} solid {colors.green-hero}"
    placement: "top-left, index label e.g. ✓ PROVEN / 01"
    description: "Opens every content frame except brand end-card."
  benchmark-receipt:
    background: "{colors.paper-raised}"
    border: "2px solid {colors.ink}"
    radius: "4–8px"
    rotation: "±1–2deg"
    rows: "IBM Plex Mono uppercase header + proof rows"
    description: "Hero device — recurs frames 0–2. Carries WML → tieout stats."
  proven-stamp:
    border: "6px solid {colors.orange}"
    shape: "circle"
    rotation: "-12deg"
    mixBlendMode: "multiply"
    description: "SLAM on authority beat — one per hook frame max."
  ticket-slip:
    background: "{colors.paper-raised}"
    border: "2px solid {colors.ink}"
    radius: "6px"
    rotation: "2–5deg"
    ghost: "6–10px down-right {colors.green} or {colors.orange} duplicate"
    description: "Stat callouts (+9pp, 74.67% tease) that SLAM from above."
  fg-occluder:
    description: "Printer slot lip, spreadsheet pass photo — sandwich depth."
  caption-rail:
    borderTop: "1px solid rgba(26,26,26,0.08)"
    placement: "bottom 7%, full width minus slide-pad"
    description: "Phase 1 burn-in; Phase 2 may slim to karaoke rail."

hero_device:
  name: benchmark-receipt
  arc: "WML proof (frame 0–1) → comparison context (frame 2) → absent by lesson (type takes over)"

motion:
  default_ease: "power3.out"
  paper_steps: "steps(4) or steps(5) on slips and stamps"
  land_not_fade: "opacity 0→1 via gsap.set on arrivals; no 2s soft fades"
  sfx_sync: "every SLAM lands on paper-drop / stamp-thud SFX cue"
  whip_exit: "blur + x-translate between frames"
  ambient_hold: "after primary reveals, keep 12–24px independent drift on 1–2 layers (dither, slips, cards) — never static holds"
  build_order: "paper field → structure/occluder → factual primary → support layer → display type"
  ghost_offset: "one orange voltage duplicate behind hero type per frame max (fondof day-1)"
  captions: "word-level karaoke rail — gsap.set className only, suppress on end card"

---

# tieout — frame layer

## Three layers (every content frame)

1. **BG** — dither plate (living texture, frozen layout grid)
2. **MID** — benchmark receipt / bar tiles / kinetic type
3. **FG** — occluder (printer slot / spreadsheet pass) + short MG type

## Build order (never dump at t=0)

1. Plate + kicker + rule draw
2. FG occluder seats (structure)
3. Receipt or chart skeleton enters
4. Objects SLAM on beat (stamp, slips, bars)
5. Display type / stats
6. Caption rail last

## Integrity

- WML 74.67% = institutional anchor; tieout ship 68% = our result
- Never claim fine-tune won this ship (clone-run config parity)
- Stats from SUBMISSION.md only
