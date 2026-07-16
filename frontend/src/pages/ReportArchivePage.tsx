import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Download, FileText } from "lucide-react";
import { api, type ScanRecord } from "../lib/api";
import { pageVariants, staggerContainer, staggerItem } from "../lib/animations";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export default function ReportArchivePage() {
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .scans()
      .then(setScans)
      .catch(() => setScans([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Report Archive</h2>
          <p className="text-sm text-cyber-muted">
            Enterprise Security Audit Reports — executive summaries for every scan.
          </p>
        </div>
        <a
          href={`${API_BASE}/analytics/export`}
          className="cyber-btn"
          target="_blank"
          rel="noreferrer"
        >
          <Download className="h-4 w-4" />
          Download Full Audit Report
        </a>
      </div>

      {loading ? (
        <div className="glass-panel p-8 text-center text-cyber-muted">Loading archive…</div>
      ) : scans.length === 0 ? (
        <div className="glass-panel p-12 text-center">
          <FileText className="mx-auto mb-4 h-12 w-12 text-cyber-muted" />
          <p className="text-cyber-muted">No scans archived yet. Run a Red-Team scenario to generate reports.</p>
        </div>
      ) : (
        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-3">
          {scans
            .slice()
            .reverse()
            .map((scan) => (
              <motion.div
                key={scan.scan_id}
                variants={staggerItem}
                className="glass-panel flex flex-wrap items-center justify-between gap-4 p-5"
              >
                <div>
                  <p className="font-mono text-sm font-semibold">{scan.scan_id}</p>
                  <p className="text-xs text-cyber-muted">
                    {scan.repo_path?.split(/[/\\]/).pop()} · {scan.timestamp?.slice(0, 19)}
                  </p>
                  <p className="mt-1 text-xs text-cyber-muted">
                    {scan.findings?.length || 0} findings · {scan.sbom_risks?.length || 0} SBOM risks
                    {scan.self_correction_triggered && " · Autopsy corrected"}
                  </p>
                </div>
                <a
                  href={`${API_BASE}/analytics/export?scan_id=${scan.scan_id}`}
                  className="inline-flex items-center gap-2 rounded-lg border border-cyber-border px-4 py-2 text-sm text-cyber-accent hover:bg-cyan-500/10"
                  target="_blank"
                  rel="noreferrer"
                >
                  <Download className="h-4 w-4" />
                  Export PDF/Markdown
                </a>
              </motion.div>
            ))}
        </motion.div>
      )}
    </motion.div>
  );
}
