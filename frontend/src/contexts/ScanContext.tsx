import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import {
  api,
  parseScanError,
  pollScan,
  type AnalyticsSummary,
  type ResilienceMetrics,
  type ScanResult,
  type ScanStatus,
} from "../lib/api";

export type ThreatLevel = "idle" | "cloning" | "scanning" | "threat";
export type AppPhase = "splash" | "landing" | "command";

export interface ToastState {
  message: string;
  variant: "warning" | "success" | "info";
}

interface ScanContextValue {
  phase: AppPhase;
  setPhase: (p: AppPhase) => void;
  activePage: string;
  setActivePage: (p: string) => void;
  repoPath: string;
  setRepoPath: (p: string) => void;
  scanning: boolean;
  cloning: boolean;
  scanResult: ScanResult | null;
  feed: ScanStatus["feed"];
  feedStatus: string;
  summary: AnalyticsSummary | null;
  resilience: ResilienceMetrics | null;
  threatLevel: ThreatLevel;
  toast: ToastState | null;
  setToast: (t: ToastState | null) => void;
  handleScan: (path?: string) => Promise<void>;
  refreshMetrics: () => Promise<void>;
}

const ScanContext = createContext<ScanContextValue | null>(null);

function computeThreatLevel(
  scanning: boolean,
  feedStatus: string,
  feed: ScanStatus["feed"],
  scanResult: ScanResult | null
): ThreatLevel {
  if (feedStatus === "cloning" || feed.some((f) => f.stage === "cloning")) return "cloning";
  if (scanning || ["scanning", "sbom", "codebreaker", "autopsy", "queued"].includes(feedStatus)) {
    return "scanning";
  }
  if (scanResult) {
    const threats =
      (scanResult.findings?.length || 0) + (scanResult.sbom_risks?.length || 0);
    if (threats > 0) return "threat";
  }
  return "idle";
}

function githubErrorMessage(raw: string): string {
  const lower = raw.toLowerCase();
  if (lower.includes("not found")) return "GitHub repo not found — check the URL.";
  if (lower.includes("private") || lower.includes("authentication")) {
    return "Cannot clone — repository is private or requires authentication.";
  }
  if (lower.includes("invalid") && lower.includes("github")) {
    return "Invalid GitHub URL format.";
  }
  if (lower.includes("git is not installed")) return "Server error: Git is not installed.";
  return raw;
}

export function ScanProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<AppPhase>("splash");
  const [activePage, setActivePage] = useState("war-room");
  const [repoPath, setRepoPath] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [feed, setFeed] = useState<ScanStatus["feed"]>([]);
  const [feedStatus, setFeedStatus] = useState("idle");
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [resilience, setResilience] = useState<ResilienceMetrics | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);
  const prevFeedLen = useRef(0);

  const cloning = feedStatus === "cloning" || feed.some((f) => f.stage === "cloning");

  const refreshMetrics = useCallback(async () => {
    try {
      const [s, r] = await Promise.all([api.summary(), api.resilience()]);
      setSummary(s);
      setResilience(r);
    } catch {
      /* backend starting */
    }
  }, []);

  useEffect(() => {
    refreshMetrics();
    const id = setInterval(refreshMetrics, 5000);
    return () => clearInterval(id);
  }, [refreshMetrics]);

  useEffect(() => {
    const rejected = feed.some(
      (f) =>
        f.message.toLowerCase().includes("corrected") ||
        f.message.toLowerCase().includes("false positive")
    );
    if (feed.length > prevFeedLen.current && rejected) {
      setToast({
        message: "Autopsy rejected false positive — self-correction engaged",
        variant: "warning",
      });
    }
    prevFeedLen.current = feed.length;
  }, [feed]);

  const handleScan = useCallback(
    async (path?: string) => {
      const target = (path ?? repoPath).trim();
      if (!target) return;
      setRepoPath(target);
      setScanning(true);
      setScanResult(null);
      setFeed([]);
      setFeedStatus("queued");
      prevFeedLen.current = 0;
      setActivePage("war-room");

      const isRemote = target.toLowerCase().startsWith("http");
      if (isRemote) {
        setFeedStatus("cloning");
      }

      try {
        const { scan_id } = await api.startScan(target);
        const stop = pollScan(scan_id, (status) => {
          setFeed(status.feed);
          setFeedStatus(status.status);
          if (status.status === "complete" && status.result) {
            setScanResult(status.result);
            setScanning(false);
            refreshMetrics();
            if (status.result.self_correction_triggered) {
              setToast({ message: "Verification complete — threat profile refined", variant: "success" });
            }
          }
          if (status.status === "error") {
            setScanning(false);
            const last = status.feed[status.feed.length - 1];
            const errMsg = last?.message || "Scan failed";
            setToast({ message: githubErrorMessage(errMsg.replace(/^Error:\s*/i, "")), variant: "warning" });
          }
        });
        setTimeout(() => stop(), 300000);
      } catch (err) {
        const msg = githubErrorMessage(parseScanError(err));
        setFeed([{ timestamp: new Date().toISOString(), message: msg, stage: "error" }]);
        setFeedStatus("error");
        setScanning(false);
        setToast({ message: msg, variant: "warning" });
      }
    },
    [repoPath, refreshMetrics]
  );

  const threatLevel = computeThreatLevel(scanning, feedStatus, feed, scanResult);

  return (
    <ScanContext.Provider
      value={{
        phase,
        setPhase,
        activePage,
        setActivePage,
        repoPath,
        setRepoPath,
        scanning,
        cloning,
        scanResult,
        feed,
        feedStatus,
        summary,
        resilience,
        threatLevel,
        toast,
        setToast,
        handleScan,
        refreshMetrics,
      }}
    >
      {children}
    </ScanContext.Provider>
  );
}

export function useScan() {
  const ctx = useContext(ScanContext);
  if (!ctx) throw new Error("useScan must be used within ScanProvider");
  return ctx;
}
