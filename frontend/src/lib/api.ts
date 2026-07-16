const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export interface Finding {
  file_path: string;
  vulnerability_type: string;
  severity: string;
  description: string;
}

export interface SBOMRisk {
  name: string;
  version: string;
  risk_level: string;
  transitive_of?: string | null;
  notes?: string;
  ecosystem?: string;
}

export interface ScanResult {
  scan_id: string;
  repo_path: string;
  files_scanned: number;
  findings: Finding[];
  sbom_risks?: SBOMRisk[];
  sbom_graph?: { from: string; to: string; type: string }[];
  sbom_assessment?: string;
  audit_status?: string;
  retry_count?: number;
  self_correction_triggered?: boolean;
  advisory_file?: string;
}

export interface SSEProgressEvent {
  scan_id: string;
  stage: string;
  message: string;
  status: "active" | "done" | "error";
  timestamp: string;
  ui_status?: "idle" | "scanning" | "verifying" | "breach" | "secure";
  reasoning?: string;
  outcome?: "secure" | "breach";
  result?: ScanResult;
}

export interface AnalyticsSummary {
  total_scans: number;
  total_files_scanned: number;
  total_vulnerabilities_caught: number;
  total_self_corrections: number;
  autopsy_win_rate_pct: number;
  severity_breakdown: Record<string, number>;
}

export interface ResilienceMetrics {
  resilience_score: number;
  false_positive_correction_rate: number;
  detection_precision: number;
  false_positive_attempts: number;
  false_positives_corrected: number;
  total_scans: number;
}

export interface ScanRecord {
  scan_id: string;
  timestamp?: string;
  repo_path?: string;
  findings?: Finding[];
  sbom_risks?: SBOMRisk[];
  self_correction_triggered?: boolean;
}

export interface RedTeamFixture {
  id: string;
  name: string;
  category: string;
  description: string;
  path: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export function parseScanError(err: unknown): string {
  if (!(err instanceof Error)) return String(err);
  try {
    const parsed = JSON.parse(err.message) as { detail?: string };
    if (parsed.detail) return parsed.detail;
  } catch {
    /* plain text */
  }
  return err.message;
}

function parseSSEChunk(buffer: string): { events: SSEProgressEvent[]; rest: string } {
  const events: SSEProgressEvent[] = [];
  const parts = buffer.split("\n\n");
  const rest = parts.pop() || "";
  for (const part of parts) {
    const line = part.trim();
    if (line.startsWith("data: ")) {
      try {
        events.push(JSON.parse(line.slice(6)) as SSEProgressEvent);
      } catch {
        /* skip malformed */
      }
    }
  }
  return { events, rest };
}

export async function streamScan(
  repo_path: string,
  onEvent: (evt: SSEProgressEvent) => void
): Promise<SSEProgressEvent | null> {
  const res = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ repo_path }),
  });
  if (!res.ok) throw new Error(await res.text());
  if (!res.body) throw new Error("No SSE stream body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let last: SSEProgressEvent | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSSEChunk(buffer);
    buffer = parsed.rest;
    for (const evt of parsed.events) {
      last = evt;
      onEvent(evt);
    }
  }
  return last;
}

export const api = {
  streamScan,
  startScanSync: (repo_path: string) =>
    request<ScanResult>("/scan/sync", {
      method: "POST",
      body: JSON.stringify({ repo_path, async_scan: false }),
    }),
  summary: () => request<AnalyticsSummary>("/analytics/summary"),
  resilience: () => request<ResilienceMetrics>("/analytics/resilience"),
  scans: () => request<ScanRecord[]>("/analytics/scans"),
  fixtures: () => request<RedTeamFixture[]>("/analytics/fixtures"),
  authStatus: (session: string | null) =>
    request<{ authenticated: boolean; message?: string }>("/auth/status", {
      headers: session ? { "X-Github-Session": session } : {},
    }),
  shipToGithub: (
    session: string,
    payload: { repo_name: string; local_path: string; description?: string }
  ) =>
    request<{ repo_url: string }>("/deploy/ship", {
      method: "POST",
      headers: { "X-Github-Session": session, "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  health: () => request<{ status: string }>("/health"),
};

export { API_BASE };
