// H-MEM governed-memory sidecar for tieout.
//
// One HMEM instance per tenant (mirroring "one file per tenant" in
// harness/tenant_store.py). Every request names its tenant in the JSON body
// or the x-tenant header; there is no cross-tenant surface. Persistence is
// optional: HMEM_PERSIST_ROOT points at a directory that gets one subdir per
// tenant.
//
//   HMEM_SIDECAR_PORT (default 8737) / HMEM_SIDECAR_HOST (default 127.0.0.1)
//   npx tsx server.ts

import http from "node:http";
import path from "node:path";
import { HMEM } from "./index.ts";
import type { AddInput } from "../vendor/memoryStore.ts";
import type { FeedbackKind, MemoryLayer, MiningEventType } from "../vendor/types.ts";

const PORT = Number(process.env.HMEM_SIDECAR_PORT ?? 8737);
const HOST = process.env.HMEM_SIDECAR_HOST ?? "127.0.0.1";
const PERSIST_ROOT = process.env.HMEM_PERSIST_ROOT;

const instances = new Map<string, HMEM>();

function hmemFor(tenant: string): HMEM {
  let h = instances.get(tenant);
  if (!h) {
    h = new HMEM({
      tenant,
      persistDir: PERSIST_ROOT ? path.join(PERSIST_ROOT, tenant) : undefined,
    });
    instances.set(tenant, h);
  }
  return h;
}

type Body = Record<string, unknown> & { tenant?: string };

function tenantOf(body: Body, req: http.IncomingMessage): string {
  const t = body.tenant ?? req.headers["x-tenant"];
  if (typeof t !== "string" || t.trim() === "") {
    throw new HttpError(400, "tenant is required");
  }
  if (t.includes("/") || t.includes("..")) {
    throw new HttpError(400, "invalid tenant");
  }
  return t;
}

class HttpError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function readBody(req: http.IncomingMessage): Promise<Body> {
  const chunks: Buffer[] = [];
  for await (const c of req) chunks.push(c as Buffer);
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Body;
  } catch {
    throw new HttpError(400, "body must be JSON");
  }
}

const routes: Record<string, (body: Body, h: HMEM) => unknown | Promise<unknown>> = {
  "POST /memory/add": (b, h) => h.store.add(b.input as AddInput),
  "POST /memory/query": (b, h) =>
    h.query(b.query as string, b.opts as Parameters<HMEM["query"]>[1]),
  "POST /memory/feedback": (b, h) =>
    h.feedback(b.memoryId as string, b.kind as FeedbackKind),
  "POST /memory/mine": (b, h) =>
    h.mine(b.event as MiningEventType, b.text as string, b.opts as { chatId?: string }),
  "GET /memory/all": (_b, h) => h.store.all(),
  "POST /memory/get": (b, h) => h.store.get(b.memoryId as string) ?? null,
  "POST /memory/promote": (b, h) =>
    h.store.promote(b.memoryId as string, b.layer as MemoryLayer),
  "POST /memory/supersede": (b, h) =>
    h.store.update(b.memoryId as string, { supersededBy: b.by as string }),
  "GET /ledger": (_b, h) => h.ledger.all(),
  "GET /ledger/stats": (_b, h) => h.ledger.stats(),
  "POST /sleep/preview": (_b, h) => h.sleep.preview(),
  "POST /sleep/execute": (_b, h) => h.sleep.execute(),
  "POST /sleep/restore": (b, h) => h.sleep.restore(b.backupId as string),
  "POST /dream/run": (_b, h) => h.dreaming.dream(),
  "GET /dream/pending": (_b, h) => h.dreaming.pending(),
  "POST /dream/approve": (b, h) => h.dreaming.approve(b.proposalId as string),
  "POST /dream/reject": (b, h) => h.dreaming.reject(b.proposalId as string),
  "POST /conflicts/scan": (_b, h) => h.conflicts.scan(),
  "GET /conflicts/queue": (_b, h) => h.conflicts.queue(),
};

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "localhost"}`);
  const send = (status: number, payload: unknown) => {
    res.writeHead(status, { "content-type": "application/json" });
    res.end(JSON.stringify(payload));
  };

  try {
    if (req.method === "GET" && url.pathname === "/healthz") {
      send(200, { ok: true, engine: "hmem", tenants: instances.size });
      return;
    }
    const key = `${req.method} ${url.pathname}`;
    const handler = routes[key];
    if (!handler) {
      send(404, { ok: false, error: `no route ${key}` });
      return;
    }
    const body = await readBody(req);
    const h = hmemFor(tenantOf(body, req));
    send(200, { ok: true, data: await handler(body, h) });
  } catch (err) {
    if (err instanceof HttpError) {
      send(err.status, { ok: false, error: err.message });
    } else {
      send(500, { ok: false, error: (err as Error).message });
    }
  }
});

server.listen(PORT, HOST, () => {
  console.log(`hmem sidecar listening on http://${HOST}:${PORT} (persist: ${PERSIST_ROOT ?? "memory"})`);
});
