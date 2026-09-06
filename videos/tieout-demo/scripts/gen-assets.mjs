#!/usr/bin/env node
/**
 * Generate tieout demo cutouts via ElevenLabs Flows Image API.
 * POST /v1/flows/image → poll GET /v1/flows/image/{id}
 * Requires ELEVENLABS_API_KEY with image generation (Pro+).
 *
 *   node scripts/gen-assets.mjs [--only char-analyst-overwhelmed,...]
 *   node scripts/gen-assets.mjs --matte   # run hyperframes remove-background on raw/
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const RAW = join(ROOT, "raw-assets");
const ASSETS = join(ROOT, "assets");

const IDENTITY =
  "Full-body flat matte editorial illustration, subtle paper grain, plain solid warm light-gray background #e8e0d4, soft even lighting, clean unbroken silhouette, entire body head to shoes, absolutely no text letters words logos watermarks symbols anywhere.";

const JOBS = [
  {
    name: "char-analyst-overwhelmed",
    aspect_ratio: "3:4",
    prompt: `${IDENTITY} A tired office analyst in their 30s, business-casual cream shirt with rolled sleeves, BOTH hands on top of head in stress, shoulders hunched, eyes wide, standing three-quarter facing viewer. Empty hands, no clipboard.`,
  },
  {
    name: "char-analyst-relief",
    aspect_ratio: "3:4",
    prompt: `${IDENTITY} Same analyst character relieved and smiling, one hand thumbs-up, other hand loose at side, shoulders relaxed, three-quarter facing viewer.`,
  },
  {
    name: "char-specialized-agent",
    aspect_ratio: "3:4",
    prompt: `${IDENTITY} Confident tech specialist in simple dark green zip jacket over light shirt, upright posture, one hand pointing decisively at an invisible screen to the side, sharp calm expression, three-quarter facing viewer. No devices visible in hands.`,
  },
  {
    name: "char-generic-ai",
    aspect_ratio: "3:4",
    prompt: `${IDENTITY} Soft ambiguous humanoid figure made of faint grey fog and wireframe hints, slumped uncertain posture, arms hanging, looking down, three-quarter facing viewer. Feels like a generic chatbot avatar, not heroic.`,
  },
  {
    name: "prop-spreadsheet-pass",
    aspect_ratio: "16:9",
    prompt:
      "Wide matte illustration of a busy analyst desk viewed from slightly above: open laptop showing a blank spreadsheet grid with highlighted orange cells, coffee mug, sticky notes with NO readable text, papers stacked, warm office light. Flat editorial collage style, no people, no text, no logos, plain warm paper background at edges.",
  },
];

function parseArgs(argv) {
  const out = { only: null, matte: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--only") out.only = argv[++i].split(",").map((s) => s.trim());
    else if (a === "--matte") out.matte = true;
    else throw new Error(`unknown arg ${a}`);
  }
  return out;
}

async function loadKey() {
  if (process.env.ELEVENLABS_API_KEY) return process.env.ELEVENLABS_API_KEY;
  for (const envPath of [
    join(ROOT, ".env"),
    join(ROOT, "../../.env"),
    "/Users/udingethe/Dev/fondof/.env",
    "/Users/udingethe/Dev/tieout/.env",
  ]) {
    if (!existsSync(envPath)) continue;
    const raw = await readFile(envPath, "utf8");
    for (const line of raw.split("\n")) {
      const t = line.trim();
      if (!t.startsWith("ELEVENLABS_API_KEY=")) continue;
      let v = t.slice("ELEVENLABS_API_KEY=".length).trim();
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'")))
        v = v.slice(1, -1);
      return v;
    }
  }
  return null;
}

async function createImage(key, job) {
  const res = await fetch("https://api.elevenlabs.io/v1/flows/image", {
    method: "POST",
    headers: {
      "xi-api-key": key,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model_id: "bytedance-seedream-5-lite",
      prompt: job.prompt,
      aspect_ratio: job.aspect_ratio,
      resolution: "2K",
    }),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`create ${job.name}: ${res.status} ${text.slice(0, 400)}`);
  return JSON.parse(text);
}

async function pollImage(key, id, label) {
  for (let i = 0; i < 90; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    const res = await fetch(`https://api.elevenlabs.io/v1/flows/image/${id}`, {
      headers: { "xi-api-key": key },
    });
    const data = await res.json();
    if (data.status === "completed" && data.content_url) return data;
    if (data.status === "failed")
      throw new Error(`${label} failed: ${data.error_message || data.failure_reason}`);
    process.stderr.write(`  … ${label} ${data.status} (${i + 1})\n`);
  }
  throw new Error(`${label} timed out`);
}

async function download(url, dest) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`download ${dest}: ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await writeFile(dest, buf);
  return buf.length;
}

async function matteAll() {
  await mkdir(ASSETS, { recursive: true });
  for (const job of JOBS) {
    const rawJpg = join(RAW, `${job.name}.jpg`);
    const rawPng = join(RAW, `${job.name}.png`);
    const src = existsSync(rawPng) ? rawPng : rawJpg;
    if (!existsSync(src)) {
      console.warn(`skip matte (missing raw): ${job.name}`);
      continue;
    }
    const out = join(ASSETS, `${job.name}.png`);
    const r = spawnSync(
      "npx",
      ["--yes", "hyperframes@0.8.30", "remove-background", src, "-o", out],
      { cwd: ROOT, stdio: "inherit" },
    );
    if (r.status !== 0) process.exit(r.status ?? 1);
    console.log(`✓ matte ${job.name} → assets/`);
  }
}

const args = parseArgs(process.argv.slice(2));
if (args.matte) {
  await matteAll();
  process.exit(0);
}

const key = await loadKey();
if (!key) {
  console.error("ELEVENLABS_API_KEY missing");
  process.exit(1);
}

const jobs = args.only ? JOBS.filter((j) => args.only.includes(j.name)) : JOBS;
await mkdir(RAW, { recursive: true });

for (const job of jobs) {
  const started = Date.now();
  console.log(`→ ${job.name}`);
  const created = await createImage(key, job);
  const id = created.id;
  const done = await pollImage(key, id, job.name);
  const ext = done.content_mime_type?.includes("png") ? "png" : "jpg";
  const outPath = join(RAW, `${job.name}.${ext}`);
  const bytes = await download(done.content_url, outPath);
  await writeFile(
    join(RAW, `${job.name}.json`),
    JSON.stringify(
      {
        provider: "elevenlabs",
        model_id: "bytedance-seedream-5-lite",
        generation_id: id,
        prompt: job.prompt,
        aspect_ratio: job.aspect_ratio,
        bytes,
        ms: Date.now() - started,
      },
      null,
      2,
    ),
  );
  console.log(`✓ ${job.name} → raw-assets/${job.name}.${ext} (${bytes} bytes, ${Date.now() - started}ms)`);
}

console.log("\nNext: node scripts/gen-assets.mjs --matte");
