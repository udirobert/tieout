#!/usr/bin/env node
/**
 * ElevenLabs TTS via REST (no Python SDK).
 * Reads ELEVENLABS_API_KEY from repo-root .env or env.
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const PROJECT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const REPO_ROOT = resolve(PROJECT, "../..");
const DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"; // George

function parseArgs(argv) {
  const out = { voice: DEFAULT_VOICE, model: "eleven_multilingual_v2" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--voice") out.voice = argv[++i];
    else if (a === "--model") out.model = argv[++i];
  }
  return out;
}

async function loadKey() {
  if (process.env.ELEVENLABS_API_KEY) return process.env.ELEVENLABS_API_KEY;
  for (const p of [join(REPO_ROOT, ".env"), join(PROJECT, ".env")]) {
    if (!existsSync(p)) continue;
    const raw = await readFile(p, "utf8");
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

function parseScript(md) {
  const out = [];
  let cur = null;
  const flush = () => {
    if (cur && cur.text.trim()) out.push({ ...cur, text: cur.text.trim() });
    cur = null;
  };
  for (const line of md.split(/\r?\n/)) {
    const h = line.match(/^#{2,3}\s+.*?\(frame\s+(\d+)\)/i);
    if (h) {
      flush();
      cur = { frame: Number(h[1]), text: "" };
      continue;
    }
    if (!cur) continue;
    if (/^\s*\*\*/.test(line)) continue;
    const m = line.match(/^(?: {4,}|\t)(.+)$/);
    if (m) cur.text += (cur.text ? " " : "") + m[1].trim();
  }
  flush();
  return out;
}

function wordsFromAlignment(text, alignment) {
  if (!alignment?.characters?.length) {
    const parts = text.split(/\s+/).filter(Boolean);
    return { words: parts.map((t) => ({ id: t, text: t, start: 0, end: 0 })), duration: 0 };
  }
  const chars = alignment.characters;
  const starts = alignment.character_start_times_seconds;
  const ends = alignment.character_end_times_seconds;
  const words = [];
  let buf = "";
  let wStart = 0;
  let wEnd = 0;
  const flush = () => {
    const t = buf.trim();
    if (t) words.push({ id: t.replace(/[^\w'-]/g, "") || t, text: t, start: wStart, end: wEnd });
    buf = "";
  };
  for (let i = 0; i < chars.length; i++) {
    const ch = chars[i];
    const s = starts[i] ?? 0;
    const e = ends[i] ?? s;
    if (/\s/.test(ch)) { flush(); continue; }
    if (!buf) wStart = s;
    buf += ch;
    wEnd = e;
  }
  flush();
  const duration = ends.length ? ends[ends.length - 1] : 0;
  return { words, duration };
}

function ffmpegMp3ToWav(mp3Path, wavPath) {
  const r = spawnSync("ffmpeg", ["-y", "-i", mp3Path, "-ac", "1", "-ar", "44100", wavPath], { stdio: "ignore" });
  if (r.status !== 0) throw new Error(`ffmpeg failed for ${mp3Path}`);
}

function ffprobeDuration(wavPath) {
  return Number(
    spawnSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", wavPath])
      .stdout.toString().trim(),
  );
}

const args = parseArgs(process.argv.slice(2));
const key = await loadKey();
if (!key) {
  console.error("ELEVENLABS_API_KEY missing");
  process.exit(1);
}

const script = parseScript(await readFile(join(PROJECT, "SCRIPT.md"), "utf8"));
if (!script.length) {
  console.error("no spoken lines in SCRIPT.md (use 'Frame N' in headers)");
  process.exit(1);
}

const voiceDir = join(PROJECT, "assets", "voice");
await mkdir(voiceDir, { recursive: true });

const voices = [];
for (const line of script) {
  const id = String(line.frame).padStart(2, "0");
  const res = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${args.voice}/with-timestamps`,
    {
      method: "POST",
      headers: { "xi-api-key": key, "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        text: line.text,
        model_id: args.model,
        output_format: "mp3_44100_128",
        voice_settings: { stability: 0.45, similarity_boost: 0.75, style: 0.12, use_speaker_boost: true, speed: 1.15 },
      }),
    },
  );
  if (!res.ok) {
    console.error(`TTS ${id} ${res.status}: ${(await res.text()).slice(0, 600)}`);
    process.exit(1);
  }
  const json = await res.json();
  const mp3Path = join(voiceDir, `${id}.mp3`);
  const wavPath = join(voiceDir, `${id}.wav`);
  await writeFile(mp3Path, Buffer.from(json.audio_base64, "base64"));
  ffmpegMp3ToWav(mp3Path, wavPath);
  const { words, duration } = wordsFromAlignment(line.text, json.alignment);
  const duration_s = Number((duration || ffprobeDuration(wavPath)).toFixed(3));
  voices.push({
    id,
    frame: line.frame,
    path: `assets/voice/${id}.wav`,
    duration_s,
    words: words.map((w) => ({
      id: w.id,
      text: w.text,
      start: Number(w.start.toFixed(3)),
      end: Number(w.end.toFixed(3)),
    })),
  });
  console.error(`voice ${id}: ${duration_s}s`);
}

const total_duration_s = voices.reduce((a, v) => a + v.duration_s, 0);
const meta = {
  tts_provider: "elevenlabs",
  voice_id: args.voice,
  bgm: null,
  bgm_pending: false,
  voices,
  sfx: [],
  total_duration_s: Number(total_duration_s.toFixed(3)),
};
await writeFile(join(PROJECT, "audio_meta.json"), JSON.stringify(meta, null, 2) + "\n");
console.error(`wrote audio_meta.json (${voices.length} voices, ${total_duration_s.toFixed(1)}s)`);
