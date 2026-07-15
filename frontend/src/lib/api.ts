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
}

export interface ScanStatus {
  scan_id: string;
  status: string;
  feed: { timestamp: string; message: string; stage: string }[];
  result: ScanResult | null;
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || res.statusText);
  }
  return res.json();
}

export const api = {
  startScan: (repo_path: string) =>
    request<{ scan_id: string; status: string; message: string }>(
      "/codebreaker/scan",
      { method: "POST", body: JSON.stringify({ repo_path, async_scan: true }) }
    ),
  scanStatus: (scan_id: string) =>
    request<ScanStatus>(`/scan/${scan_id}/status`),
  summary: () => request<AnalyticsSummary>("/analytics/summary"),
  resilience: () => request<ResilienceMetrics>("/analytics/resilience"),
  health: () => request<{ status: string }>("/health"),
};

export function pollScan(
  scan_id: string,
  onUpdate: (status: ScanStatus) => void,
  intervalMs = 1000
): () => void {
  let active = true;
  const tick = async () => {
    if (!active) return;
    try {
      const status = await api.scanStatus(scan_id);
      onUpdate(status);
      if (status.status === "complete" || status.status === "error") return;
    } catch {
      /* retry next tick */
    }
    if (active) setTimeout(tick, intervalMs);
  };
  tick();
  return () => {
    active = false;
  };
}
