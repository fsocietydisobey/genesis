/**
 * Staleness classifier — derives a "fresh / stale / stuck / hitl-idle"
 * label for each thread based on how long since `last_updated` relative
 * to its `status`.
 *
 * Why client-side: the API already serializes both fields. Computing
 * staleness here avoids a server-side staleness column that would
 * inevitably go stale-on-the-wire (the API response is itself a
 * snapshot in time). The thread list polls every 2s, so re-renders
 * naturally re-evaluate staleness.
 *
 * Tiers:
 *   - `fresh`     — within thresholds for its status, or status=idle
 *   - `stale`     — running/starting thread quiet >5 min (worth flagging)
 *   - `stuck`     — running/starting thread quiet >15 min (likely hung)
 *   - `hitl-idle` — paused thread quiet >15 min (HITL prompt abandoned;
 *                   distinct from stuck because pausing is intentional)
 *
 * Thresholds are per-app-defaults. A future iteration could pull a
 * project-specific threshold from metadata for graphs that legitimately
 * have minutes-long node latency (e.g. chimera's pipeline). For now
 * 5/15 covers the common case.
 */

import type { ThreadSummary } from "@/api";

export type Staleness = "fresh" | "stale" | "stuck" | "hitl-idle";

export const STALE_THRESHOLD_MS = 5 * 60 * 1000;
export const STUCK_THRESHOLD_MS = 15 * 60 * 1000;

export function getStaleness(thread: ThreadSummary, now: number = Date.now()): Staleness {
  if (!thread.last_updated) return "fresh";
  const updated = new Date(thread.last_updated).getTime();
  if (!Number.isFinite(updated)) return "fresh";
  const age = now - updated;

  if (thread.status === "running" || thread.status === "starting") {
    if (age >= STUCK_THRESHOLD_MS) return "stuck";
    if (age >= STALE_THRESHOLD_MS) return "stale";
    return "fresh";
  }
  if (thread.status === "paused") {
    if (age >= STUCK_THRESHOLD_MS) return "hitl-idle";
    return "fresh";
  }
  return "fresh";
}

/** Order for sorting flagged threads to the top within a status group. */
export const STALENESS_PRIORITY: Record<Staleness, number> = {
  stuck: 0,
  stale: 1,
  "hitl-idle": 2,
  fresh: 3,
};

/** Tally staleness across an array of threads — used for the header chip. */
export function countStaleness(threads: ThreadSummary[]): Record<Staleness, number> {
  const out: Record<Staleness, number> = { fresh: 0, stale: 0, stuck: 0, "hitl-idle": 0 };
  const now = Date.now();
  for (const t of threads) {
    out[getStaleness(t, now)] += 1;
  }
  return out;
}
