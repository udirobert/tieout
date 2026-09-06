#!/usr/bin/env node
/**
 * Runware fallback for tieout cutouts when ElevenLabs key lacks image_video_generation.
 * Same jobs as gen-assets.mjs. Loads RUNWARE_API_KEY from yaler .env or env.
 */
import { createClient } from "@runware/sdk";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const RAW = join(ROOT, "raw-assets");

const IDENTITY =
  "Full-body flat matte editorial illustration, subtle paper grain, plain solid warm light-gray background, soft even lighting, clean unbroken silhouette, entire body head to shoes, absolutely no text letters words logos watermarks.";

const JOBS = [
  {
    name: "char-analyst-overwhelmed",
    width: 1024,
    height: 1536,
    prompt: `${IDENTITY} Office analyst in 30s, cream rolled-sleeve shirt, both hands gripping head in stress, hunched shoulders, three-quarter pose.`,
  },
  {
    name: "char-specialized-agent",
    width: 1024,
    height: 1536,
    prompt: `${IDENTITY} Confident specialist in dark green jacket, upright, one hand pointing aside decisively, calm sharp expression, three-quarter pose.`,
  },
  {
    name: "char-generic-ai",
    width: 1024,
    height: 1536,
    prompt: `${IDENTITY} Soft grey fog humanoid, slumped uncertain posture, arms hanging, looking down, generic AI feel, three-quarter pose.`,
  },
  {
    name: "prop-spreadsheet-pass",
    width: 1536,
    height: 1024,
    prompt:
      "Wide matte illustration of busy analyst desk from above: laptop with blank spreadsheet grid and orange highlighted cells, coffee mug, sticky notes with no readable text, stacked papers, warm light, no people, no text, no logos.",
  },
];

async function loadKey() {
  if (process.env.RUNWARE_API_KEY) return process.env.RUNWARE_API_KEY;
  for (const p of ["/Users/udingethe/Dev/yaler/.env", join(ROOT, "../../.env")]) {
    if (!existsSync(p)) continue;
    const raw = await readFile(p, "utf8");
    for (const line of raw.split("\n")) {
      const t = line.trim();
      if (!t.startsWith("RUNWARE_API_KEY=")) continue;
      let v = t.slice("RUNWARE_API_KEY=".length).trim();
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'")))
        v = v.slice(1, -1);
      return v;
    }
  }
  return null;
}

const only = process.argv.includes("--only")
  ? process.argv[process.argv.indexOf("--only") + 1].split(",").map((s) => s.trim())
  : null;
const matte = process.argv.includes("--matte");

if (matte) {
  const { spawnSync: sp } = await import("node:child_process");
  for (const job of JOBS) {
    const src = [join(RAW, `${job.name}.png`), join(RAW, `${job.name}.jpg`)].find((p) =>
      existsSync(p),
    );
    if (!src) continue;
    const out = join(ROOT, "assets", `${job.name}.png`);
    await mkdir(join(ROOT, "assets"), { recursive: true });
    sp("npx", ["--yes", "hyperframes@0.8.30", "remove-background", src, "-o", out], {
      cwd: ROOT,
      stdio: "inherit",
    });
  }
  process.exit(0);
}

const key = await loadKey();
if (!key) {
  console.error("RUNWARE_API_KEY missing");
  process.exit(1);
}

const jobs = only ? JOBS.filter((j) => only.includes(j.name)) : JOBS;
const client = await createClient({ apiKey: key });
await client.connect();
await mkdir(RAW, { recursive: true });

for (const job of jobs) {
  const started = Date.now();
  const [result] = await client.run({
    model: "bytedance:seedream@5.0-pro",
    positivePrompt: job.prompt,
    width: job.width,
    height: job.height,
    numberResults: 1,
    includeCost: true,
  });
  const url = result.imageURL;
  if (!url) throw new Error(`no imageURL for ${job.name}`);
  const res = await fetch(url);
  const buf = Buffer.from(await res.arrayBuffer());
  const ext = url.includes(".png") ? "png" : "jpg";
  const outPath = join(RAW, `${job.name}.${ext}`);
  await writeFile(outPath, buf);
  await writeFile(
    join(RAW, `${job.name}.json`),
    JSON.stringify({ provider: "runware", ms: Date.now() - started, cost: result.cost }, null, 2),
  );
  console.log(`✓ ${job.name} → ${outPath} (${buf.length} bytes)`);
}

console.log("Next: node scripts/gen-assets-runware.mjs --matte");
