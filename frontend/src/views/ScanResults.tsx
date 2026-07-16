import { motion } from "framer-motion";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { Download, Github, Terminal } from "lucide-react";
import type { ScanResult } from "../lib/api";
import { API_BASE } from "../lib/api";
import TacticalAdvisory from "../components/TacticalAdvisory";

interface Props {
  result: ScanResult;
  outcome: "secure" | "breach";
  githubSession: string | null;
  onShip?: () => void;
  shipping?: boolean;
}

const COLORS = ["#ef4444", "#f97316", "#eab308", "#10b981"];

function severityData(result: ScanResult) {
  const counts: Record<string, number> = { Critical: 0, High: 0, Medium: 0, Low: 0 };
  result.findings?.forEach((f) => {
    const k = f.severity.charAt(0).toUpperCase() + f.severity.slice(1).toLowerCase();
    if (k in counts) counts[k] += 1;
  });
  result.sbom_risks?.forEach((r) => {
    const k = r.risk_level.charAt(0).toUpperCase() + r.risk_level.slice(1).toLowerCase();
    if (k in counts) counts[k] += 1;
  });
  return Object.entries(counts)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));
}

export default function ScanResults({ result, outcome, githubSession, onShip, shipping }: Props) {
  const chartData = severityData(result);
  const advisoryUrl = `${API_BASE}/analytics/export?scan_id=${result.scan_id}`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      <div className="glass-panel flex flex-wrap items-center justify-between gap-4 p-6">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-cyber-muted">
            Audit Session {result.scan_id}
          </p>
          <h2 className="font-sans text-2xl font-bold">
            {outcome === "secure" ? (
              <span className="text-emerald-400">Perimeter Secure</span>
            ) : (
              <span className="text-orange-400">Tactical Advisories Issued</span>
            )}
          </h2>
          <p className="font-mono text-xs text-cyber-muted">workspace::{result.repo_path}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <a href={advisoryUrl} className="cyber-btn" target="_blank" rel="noreferrer">
            <Download className="h-4 w-4" />
            Export Advisory
          </a>
          {outcome === "secure" && (
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/30 px-5 py-3 text-sm font-semibold text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-50"
              disabled={!githubSession || shipping}
              onClick={onShip}
            >
              <Github className="h-4 w-4" />
              {shipping ? "Shipping..." : "Ship to GitHub"}
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="glass-panel p-6 lg:col-span-2">
          <h3 className="mb-4 flex items-center gap-2 font-mono text-xs uppercase tracking-[0.25em] text-cyber-accent">
            <Terminal className="h-4 w-4" />
            Severity Matrix
          </h3>
          {chartData.length === 0 ? (
            <p className="font-mono text-sm text-cyber-muted">NO_SIGNAL</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={chartData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="glass-panel p-6 lg:col-span-3">
          <TacticalAdvisory findings={result.findings || []} sbomRisks={result.sbom_risks || []} />
        </div>
      </div>
    </motion.div>
  );
}
