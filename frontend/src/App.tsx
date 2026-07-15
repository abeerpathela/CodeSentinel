import { useCallback, useEffect, useState } from "react";
import { Activity, Brain, FileWarning, ShieldCheck } from "lucide-react";
import ScanEngine from "./components/ScanEngine";
import ThreatHeatmap from "./components/ThreatHeatmap";
import AutopsyFeed from "./components/AutopsyFeed";
import RiskGraph from "./components/RiskGraph";
import {
  api,
  pollScan,
  type AnalyticsSummary,
  type ScanResult,
  type ScanStatus,
} from "./lib/api";

export default function App() {
  const [repoPath, setRepoPath] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [feed, setFeed] = useState<ScanStatus["feed"]>([]);
  const [feedStatus, setFeedStatus] = useState("idle");
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);

  const refreshSummary = useCallback(async () => {
    try {
      const s = await api.summary();
      setSummary(s);
    } catch {
      /* backend may be starting */
    }
  }, []);

  useEffect(() => {
    refreshSummary();
    const id = setInterval(refreshSummary, 5000);
    return () => clearInterval(id);
  }, [refreshSummary]);

  const handleScan = async () => {
    if (!repoPath.trim()) return;
    setScanning(true);
    setScanResult(null);
    setFeed([]);
    setFeedStatus("queued");

    try {
      const { scan_id } = await api.startScan(repoPath.trim());
      const stop = pollScan(scan_id, (status) => {
        setFeed(status.feed);
        setFeedStatus(status.status);
        if (status.status === "complete" && status.result) {
          setScanResult(status.result);
          setScanning(false);
          refreshSummary();
        }
        if (status.status === "error") {
          setScanning(false);
        }
      });
      setTimeout(() => stop(), 300000);
    } catch (err) {
      setFeed([{ timestamp: new Date().toISOString(), message: String(err), stage: "error" }]);
      setFeedStatus("error");
      setScanning(false);
    }
  };

  const riskyNodes = (scanResult?.sbom_risks || []).map((r) => r.name);

  return (
    <div className="min-h-screen p-6">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-cyber-accent">
            CodeSentinel v0.4
          </p>
          <h1 className="text-3xl font-bold tracking-tight">Analyst Dashboard</h1>
          <p className="mt-1 text-sm text-cyber-muted">
            Agentic Supply Chain Defense — Codebreaker + Autopsy + SBOM
          </p>
        </div>
        {summary && (
          <div className="flex flex-wrap gap-4">
            <Stat icon={<ShieldCheck className="h-4 w-4" />} label="Files Scanned" value={summary.total_files_scanned} />
            <Stat icon={<FileWarning className="h-4 w-4" />} label="Vulns Caught" value={summary.total_vulnerabilities_caught} />
            <Stat icon={<Brain className="h-4 w-4" />} label="Autopsy Wins" value={summary.total_self_corrections} />
            <Stat icon={<Activity className="h-4 w-4" />} label="Win Rate" value={`${summary.autopsy_win_rate_pct}%`} />
          </div>
        )}
      </header>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <ScanEngine repoPath={repoPath} onChange={setRepoPath} onScan={handleScan} scanning={scanning} />
          <ThreatHeatmap findings={scanResult?.findings || []} sbomRisks={scanResult?.sbom_risks} />
          <RiskGraph
            repoName={scanResult?.repo_path?.split(/[/\\]/).pop() || "Your Repo"}
            edges={scanResult?.sbom_graph || []}
            riskyNodes={riskyNodes}
          />
        </div>
        <div className="min-h-[480px]">
          <AutopsyFeed feed={feed} status={feedStatus} />
        </div>
      </div>
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="cyber-panel flex items-center gap-3 px-4 py-3">
      <span className="text-cyber-accent">{icon}</span>
      <div>
        <p className="text-xs text-cyber-muted">{label}</p>
        <p className="font-mono text-lg font-bold">{value}</p>
      </div>
    </div>
  );
}
