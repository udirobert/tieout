# Assets — tieout demo

Generated cutouts and props for Phase 1.5. Regenerate with:

```bash
# ElevenLabs (needs model approval — currently model_access_denied for bytedance-seedream)
node scripts/gen-assets.mjs --only prop-city-skyline,char-analyst-relief,char-generic-ai
node scripts/gen-assets.mjs --matte

# Runware fallback (used Sep 2026)
node scripts/gen-assets-runware.mjs --only prop-city-skyline,char-analyst-relief,char-generic-ai
npx hyperframes@0.8.30 remove-background raw-assets/<name>.jpg -o assets/<name>.png
```

| File | Role | Frames |
|------|------|--------|
| char-analyst-overwhelmed.png | Protagonist — stressed | frame-00-skyline (FG hero ~480px), frame-03-results (beside false-win bar) |
| char-analyst-relief.png | Protagonist — relieved | ready / unused |
| char-specialized-agent.png | Hero specialist cutout | frame-01-proof (rises with green hero), frame-05-ship (card 01) |
| char-generic-ai.png | Soft generic AI figure | ready / unused |
| prop-spreadsheet-pass.png | Desk / spreadsheet prop | frame-05-ship (card 02 art) |
| prop-city-skyline.png | Matted skyline cutout | catalog |
| raw-assets/prop-city-skyline.jpg | Dense cream-sky plate | frame-00-skyline soft mid-layer behind CSS towers (~0.4 opacity) |
