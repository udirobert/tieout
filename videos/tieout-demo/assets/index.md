# Assets — tieout demo

Generated cutouts and props for Phase 1.5. Regenerate with:

```bash
# ElevenLabs (needs image_video_generation permission on key)
node scripts/gen-assets.mjs
node scripts/gen-assets.mjs --matte

# Runware fallback (current)
node scripts/gen-assets-runware.mjs --only char-analyst-overwhelmed,...
node scripts/gen-assets-runware.mjs --matte
```

| File | Role | Frame |
|------|------|-------|
| char-analyst-overwhelmed.png | Protagonist — stressed | Hook |
| char-specialized-agent.png | Hero cutout | Hook |
| prop-spreadsheet-pass.png | FG desk occluder | Hook |

Pending: char-generic-ai, char-analyst-relief, living spreadsheet clip (Eleven video).
