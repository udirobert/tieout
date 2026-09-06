# tieout demo — design spec

## Palette

| Token | Hex | Use |
|-------|-----|-----|
| paper | `#f5f0e8` | background |
| ink | `#1a1a1a` | headlines |
| muted | `#6b6560` | body, captions |
| dither | `#e8e0d4` | texture dots |
| grey | `#b8b0a4` | Generic AI / baseline bars |
| orange | `#e07a3a` | accent / mid bar |
| green | `#2d8a4e` | Specialized / hero |
| bloom | `rgba(45,138,78,0.25)` | hero aura only |

## Typography

- Headlines: IBM Plex Sans 700–800, 56–96px
- Stats: IBM Plex Mono 600–700, 72–120px
- Captions: IBM Plex Sans 400, 28px, muted
- Labels: IBM Plex Mono 500, 14–18px uppercase tracking

## Motion doctrine

- **Land, don't fade** — arrivals use snap + whip (opacity 0→1 via set, y/x offset)
- **Living texture** — dither pattern phase-shifts; grid breathes at 3% scale
- **Frozen layout** — chart axes and type positions fixed; only values/masks animate
- **Camera** — slow push on hook; whip between characters; iris/zoom on 68%
- **Transitions** — 0.25–0.35s CSS seams between scenes (exit blur on prior)

## Characters (typographic)

1. **The Analyst** — grid cells, human-scale highlight `#e07a3a`
2. **Generic AI** — grey pill, soft drift, ~45% bar
3. **Specialized Agent** — green pill, sharp snap, 68% bar + bloom
