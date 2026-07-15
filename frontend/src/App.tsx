import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, Brain, FileWarning, Shield, ShieldCheck, Zap } from "lucide-react";
import ScanEngine from "./components/ScanEngine";
import ThreatHeatmap from "./components/ThreatHeatmap";
import AutopsyFeed from "./components/AutopsyFeed";
import RiskGraph from "./components/RiskGraph";
import SupplyChainTable from "./components/SupplyChainTable";
import {
  api,
  pollScan,
  type AnalyticsSummary,
  type ResilienceMetrics,
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
  const [resilience, setResilience] = useState<ResilienceMetrics | null>(null);
  const [hasScans, setHasScans] = useState(false);

  const refreshMetrics = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([api.summary(), api.resilience()]);
      setSummary(s);
      setResilience(r);
      setHasScans(s.total_scans > 0);
    } catch {
      /* backend starting — stay in ready state */
    }
  }, []);

  useEffect(() => {
    refreshMetrics();
    const id = setInterval(refreshMetrics, 5000);
    return () => clearInterval(id);
  }, [refreshMetrics]);

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
          setHasScans(true);
          refreshMetrics();
        }
        if (status.status === "error") setScanning(false);
      });
      setTimeout(() => stop(), 300000);
    } catch (err) {
      setFeed([{ timestamp: new Date().toISOString(), message: String(err), stage: "error" }]);
      setFeedStatus("error");
      setScanning(false);
    }
  };

  const riskyNodes = (scanResult?.sbom_risks || []).map((r) => r.name);
  const showReadyState = !hasScans && !scanning && !scanResult;

  return (
    <div className="min-h-screen p-4 md:p-6">
      <motion.header
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 flex flex-wrap items-end justify-between gap-4"
      >
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.35em] text-cyber-accent">
            Sentinel Command &amp; Control
          </p>
          <h1 className="bg-gradient-to-r from-cyan-300 to-slate-200 bg-clip-text text-3xl font-bold tracking-tight text-transparent">
            CodeSentinel Dashboard
          </h1>
          <p className="mt-1 text-sm text-cyber-muted">
            Agentic Supply Chain Defense — Codebreaker · Autopsy · SBOM
          </p>
        </div>
        {summary && hasScans && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex flex-wrap gap-3"
          >
            <Stat icon={<ShieldCheck className="h-4 w-4" />} label="Files Scanned" value={summary.total_files_scanned} />
            <Stat icon={<FileWarning className="h-4 w-4" />} label="Vulns Caught" value={summary.total_vulnerabilities_caught} />
            <Stat icon={<Brain className="h-4 w-4" />} label="Autopsy Wins" value={summary.total_self_corrections} />
            <Stat icon={<Zap className="h-4 w-4" />} label="Resilience" value={`${resilience?.resilience_score ?? 0}%`} />
          </motion.div>
        )}
      </motion.header>

      {showReadyState && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="cyber-panel mb-8 flex flex-col items-center justify-center gap-4 py-16 text-center"
        >
          <Shield className="h-16 w-16 text-cyber-accent opacity-80" />
          <h2 className="text-2xl font-semibold">Ready to Secure Infrastructure</h2>
          <p className="max-w-md text-sm text-cyber-muted">
            Enter a local repository path and launch a Shield Scan. Codebreaker (Gemini) and Autopsy
            (Groq) will analyze source code and supply-chain dependencies in real time.
          </p>
        </motion.div>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <ScanEngine repoPath={repoPath} onChange={setRepoPath} onScan={handleScan} scanning={scanning} />
          {(scanResult || hasScans) && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
              <ThreatHeatmap findings={scanResult?.findings || []} sbomRisks={scanResult?.sbom_risks} />
              <SupplyChainTable risks={scanResult?.sbom_risks || []} />
              <RiskGraph
                repoName={scanResult?.repo_path?.split(/[/\\]/).pop() || "Repository"}
                edges={scanResult?.sbom_graph || []}
                riskyNodes={riskyNodes}
              />
            </motion.div>
          )}
        </div>
        <div className="min-h-[520px]">
          <AutopsyFeed
            feed={feed}
            status={feedStatus}
            selfCorrection={
              scanResult?.self_correction_triggered ||
              feed.some((f) => f.message.toLowerCase().includes("corrected"))
            }
          />
        </div>
      </div>

      {resilience && hasScans && (
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="cyber-panel mt-6 flex flex-wrap items-center gap-6 p-4 text-xs text-cyber-muted"
        >
          <span className="flex items-center gap-1">
            <Activity className="h-3 w-3 text-cyber-accent" />
            Resilience Score: <strong className="text-cyber-text">{resilience.resilience_score}%</strong>
          </span>
          <span>FP Correction: {(resilience.false_positive_correction_rate * 100).toFixed(1)}%</span>
          <span>Detection Precision: {(resilience.detection_precision * 100).toFixed(1)}%</span>
        </motion.footer>
      )}
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
