import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export interface Connection {
  var: string;
  host: string;
  database: string;
}

export interface Project {
  name: string;
  path: string;
  detected_via: "pyproject" | "source-scan";
  has_pyproject: boolean;
  connections: Connection[];
}

export interface TopologyEdge {
  source: string;
  target: string;
}

export interface NodeMeta {
  role: string;     // empty when not classified
  label: string;    // empty → use raw node name
  summary: string;  // empty → no description available yet
}

export interface TopologyGraph {
  name: string;
  label?: string;
  summary?: string;
  role?: "orchestrator" | "subgraph" | "leaf" | "";
  source: "introspection" | "ast";
  approximate: boolean;
  error: string | null;
  layout?: "TB" | "BT" | "LR" | "RL";
  invokes?: Record<string, string>;
  nodes: string[];
  node_meta?: Record<string, NodeMeta>;
  edges: TopologyEdge[];
  mermaid: string;
}

export interface TopologyResponse {
  project: string;
  graphs: TopologyGraph[];
  combined_mermaid?: string;
  scan_status?: "enriched" | "stale" | "none";
  summary?: string;
}

export type ThreadStatus = "paused" | "running" | "starting" | "idle";

export interface ThreadSummary {
  thread_id: string;
  latest_checkpoint_id: string;
  last_updated: string | null;
  step: number | null;
  status: ThreadStatus;
  current_node: string | null;
  recent_nodes: string[];
  agent_profile: string | null;
  phase: string | null;
  // Generic grouping fields — see backend's parse_grouping +
  // metadata.thread_grouping. Always present.
  scope_kind: string;
  scope_id: string;
  stage: string;
  stage_detail: string;
}

export interface ThreadsResponse {
  project: string;
  limit: number;
  offset: number;
  since: string | null;
  scope_label: string;             // "Deliverable", "Run", "Chain", ...
  threads: ThreadSummary[];
}

export interface CheckpointDetail {
  checkpoint_id: string;
  parent_checkpoint_id: string | null;
  created_at: string | null;
  step: number | null;
  node: string | null;
  state: unknown;
  metadata: unknown;
}

export interface ThreadDetailResponse {
  project: string;
  thread_id: string;
  checkpoints: CheckpointDetail[];
}

// RTK Query slice. Live updates are via `pollingInterval: 2000` per query
// (not SSE — that lands in Phase 2). Two seconds is the spec's "live update
// within 2s" target, met identically by polling at this volume.
export const monitorApi = createApi({
  reducerPath: "monitorApi",
  baseQuery: fetchBaseQuery({ baseUrl: "/api" }),
  tagTypes: ["Projects", "Topology", "Threads"],
  endpoints: (build) => ({
    listProjects: build.query<Project[], void>({
      query: () => "/projects",
      providesTags: ["Projects"],
    }),
    getTopology: build.query<TopologyResponse, string>({
      query: (name) => `/topology/${encodeURIComponent(name)}`,
      providesTags: (_r, _e, name) => [{ type: "Topology", id: name }],
    }),
    listThreads: build.query<
      ThreadsResponse,
      { name: string; limit?: number; offset?: number }
    >({
      query: ({ name, limit = 50, offset = 0 }) =>
        `/threads/${encodeURIComponent(name)}?limit=${limit}&offset=${offset}`,
      providesTags: (_r, _e, { name }) => [{ type: "Threads", id: name }],
    }),
    getThreadDetail: build.query<
      ThreadDetailResponse,
      { name: string; threadId: string; limit?: number }
    >({
      query: ({ name, threadId, limit = 20 }) =>
        `/threads/${encodeURIComponent(name)}/${encodeURIComponent(threadId)}?limit=${limit}`,
    }),
  }),
});

export const {
  useListProjectsQuery,
  useGetTopologyQuery,
  useListThreadsQuery,
  useGetThreadDetailQuery,
} = monitorApi;
