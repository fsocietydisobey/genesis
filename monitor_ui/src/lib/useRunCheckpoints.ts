/**
 * useRunCheckpoints — fetch and merge a chronological checkpoint
 * timeline for a "run" = one primary thread + zero-or-more sibling
 * threads (same logical execution that may have spanned multiple
 * subgraphs).
 *
 * Output: a single RunCheckpoint[] sorted oldest → newest, with each
 * entry tagged by its source `thread_id` so callers can map back to
 * the originating graph (needed for cross-graph step numbering and
 * ghost rendering).
 *
 * Polling: callers pass a `pollingInterval`. Typical pattern is to
 * poll while live-tailing (state.index === null && thread is live)
 * and stop polling while replay is scrubbing. Siblings are fetched
 * once per key change — they belong to a fixed run.
 */

import { useEffect, useMemo, useState } from "react";

import type { CheckpointDetail } from "@/api";
import { useGetThreadDetailQuery } from "@/api";

export interface RunCheckpoint extends CheckpointDetail {
  thread_id: string;
}

export function useRunCheckpoints(
  projectName: string,
  primaryThreadId: string | null,
  siblingThreadIds: string[],
  pollingInterval: number,
): { checkpoints: RunCheckpoint[]; isLoading: boolean } {
  const { data, isLoading } = useGetThreadDetailQuery(
    { name: projectName, threadId: primaryThreadId ?? "", limit: 200 },
    { skip: !primaryThreadId, pollingInterval },
  );

  const [siblings, setSiblings] = useState<RunCheckpoint[]>([]);
  const siblingsKey = siblingThreadIds.slice().sort().join(",");
  useEffect(() => {
    if (siblingThreadIds.length === 0) {
      setSiblings([]);
      return;
    }
    let cancelled = false;
    Promise.all(
      siblingThreadIds.map(async (tid) => {
        try {
          const resp = await fetch(
            `/api/threads/${encodeURIComponent(projectName)}/${encodeURIComponent(tid)}?limit=200`,
          );
          if (!resp.ok) return [] as RunCheckpoint[];
          const json = await resp.json();
          const list = (json.checkpoints ?? []) as CheckpointDetail[];
          return list.map((c) => ({ ...c, thread_id: tid }));
        } catch {
          return [] as RunCheckpoint[];
        }
      }),
    ).then((arrays) => {
      if (cancelled) return;
      setSiblings(arrays.flat());
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectName, siblingsKey]);

  const merged = useMemo<RunCheckpoint[]>(() => {
    const primary: RunCheckpoint[] =
      data && primaryThreadId
        ? [...data.checkpoints]
            .reverse()
            .map((c) => ({ ...c, thread_id: primaryThreadId }))
        : [];
    if (siblings.length === 0) return primary;
    const all = [...primary, ...siblings];
    all.sort((a, b) =>
      (a.created_at ?? "").localeCompare(b.created_at ?? ""),
    );
    return all;
  }, [data, primaryThreadId, siblings]);

  return { checkpoints: merged, isLoading };
}
