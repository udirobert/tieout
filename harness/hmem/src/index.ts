// H-MEM engine for tieout, conformance entry point.
// Vendor source is the Meterless H-MEM reference (Apache-2.0) from
// github.com/meterless/meterless engines/hmem, vendored unchanged so the
// engine itself is the upstream expression of the spec; the governed-memory
// integration lives in the tenant scoping below and in harness/hmem_client.py.
//
// Conformance (from the vendored engine checkout):
//   HMEM_IMPL=/abs/path/harness/hmem/src/index.ts npx tsx conformance/runner.ts

export * from "../vendor/index.ts";

import { HMEM as VendorHMEM } from "../vendor/index.ts";
import type { HMEMOptions } from "../vendor/index.ts";

export class HMEM extends VendorHMEM {
  readonly tenant: string;

  constructor(opts: HMEMOptions & { tenant?: string } = {}) {
    const { tenant, ...rest } = opts;
    super({ ...rest, actor: rest.actor ?? `tenant:${tenant ?? "default"}` });
    this.tenant = tenant ?? "default";
  }
}
