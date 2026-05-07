/**
 * NodeInspector — opens when a node is clicked.
 *
 * Always renders the node's intent description (role + label + summary
 * from the metadata cache). When a thread is also focused, additionally
 * lists the checkpoints in that thread where this node was the current
 * node, with full deserialized state per visit.
 */

import { useGetThreadDetailQuery, type CheckpointDetail, type NodeMeta } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JsonTree } from "@/components/threads/JsonTree";
import { cn } from "@/lib/utils";

interface NodeInspectorProps {
  projectName: string;
  graphName: string;     // kept in props for caller convenience; not rendered directly
  graphLabel: string;
  node: string;
  meta: NodeMeta | undefined;
  // When set, additionally show the per-checkpoint history at this node
  // for the focused thread.
  threadId: string | null;
  onClose: () => void;
}

const ROLE_BADGE: Record<string, { label: string; className: string }> = {
  entry: { label: "entry", className: "bg-amber-500/15 text-amber-300 border-amber-500/40" },
  exit: { label: "exit", className: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40" },
  router: { label: "router", className: "bg-violet-500/15 text-violet-300 border-violet-500/40" },
  gate: { label: "gate", className: "bg-orange-500/15 text-orange-300 border-orange-500/40" },
  critic: { label: "critic", className: "bg-rose-500/15 text-rose-300 border-rose-500/40" },
  synthesis: { label: "synthesis", className: "bg-emerald-600/15 text-emerald-300 border-emerald-600/40" },
  executor: { label: "executor", className: "bg-zinc-500/15 text-zinc-300 border-zinc-500/40" },
};

export function NodeInspector({
  projectName,
  graphLabel,
  node,
  meta,
  threadId,
  onClose,
}: NodeInspectorProps) {
  const displayLabel = (meta?.label && meta.label.trim()) || node;
  const roleBadge = meta?.role ? ROLE_BADGE[meta.role] : null;

  return (
    <div className="flex h-full flex-col border-l border-border bg-card/40">
      <div className="flex items-start justify-between border-b border-border px-3 py-2 gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">node</p>
            {roleBadge ? (
              <span className={cn(
                "inline-flex items-center rounded-md border px-1.5 py-0 text-[10px] font-medium",
                roleBadge.className,
              )}>
                {roleBadge.label}
              </span>
            ) : null}
          </div>
          <h3 className="font-mono text-sm break-all mt-0.5">{displayLabel}</h3>
          {displayLabel !== node ? (
            <p className="text-[10px] text-muted-foreground/70 font-mono break-all mt-0.5">
              {node}
            </p>
          ) : null}
          <p className="text-[10px] text-muted-foreground mt-0.5">
            in <span className="font-mono">{graphLabel}</span>
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>×</Button>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-3">
        {meta?.summary ? (
          <div className="rounded-md border border-border bg-card/60 px-3 py-2 text-xs leading-relaxed text-foreground/90">
            {meta.summary}
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-border/60 px-3 py-2 text-[11px] text-muted-foreground italic">
            No description yet — re-run <code>chimera monitor rescan {projectName}</code> to
            populate node intent from the codebase.
          </div>
        )}

        {threadId ? (
          <NodeCheckpoints projectName={projectName} threadId={threadId} node={node} />
        ) : (
          <p className="text-[11px] text-muted-foreground italic">
            Focus a run in the sidebar to see this node's state at each visit.
          </p>
        )}
      </div>
    </div>
  );
}

function NodeCheckpoints({
  projectName,
  threadId,
  node,
}: {
  projectName: string;
  threadId: string;
  node: string;
}) {
  const { data, isLoading, error } = useGetThreadDetailQuery(
    { name: projectName, threadId, limit: 50 },
    { pollingInterval: 2000 },
  );

  if (isLoading) return <p className="text-xs text-muted-foreground">loading checkpoints…</p>;
  if (error) return <p className="text-xs text-destructive">{String(error)}</p>;
  if (!data) return null;

  const relevant = data.checkpoints.filter((c) => c.node === node);
  if (relevant.length === 0) {
    return (
      <p className="text-[11px] text-muted-foreground italic">
        No checkpoint in this run had <code className="font-mono">{node}</code> as
        its current node yet.
      </p>
    );
  }

  return (
    <>
      <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {relevant.length} visit{relevant.length === 1 ? "" : "s"} in focused run
      </p>
      {relevant.map((cp: CheckpointDetail) => (
        <Card key={cp.checkpoint_id}>
          <CardHeader className="space-y-1 py-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-mono">step {cp.step ?? "?"}</CardTitle>
              <Badge variant="outline" className="text-[10px]">
                {cp.created_at?.slice(0, 19) ?? "?"}
              </Badge>
            </div>
            <p className="text-[10px] text-muted-foreground font-mono">{cp.checkpoint_id}</p>
          </CardHeader>
          <CardContent className="pt-0">
            <JsonTree data={cp.state} />
          </CardContent>
        </Card>
      ))}
    </>
  );
}
