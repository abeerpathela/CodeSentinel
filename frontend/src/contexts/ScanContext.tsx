import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import {
  api,
  parseScanError,
  streamScan,
  type AnalyticsSummary,
  type ResilienceMetrics,
  type ScanResult,
  type SSEProgressEvent,
} from "../lib/api";
import type { ScanStatusMode } from "../components/SentinelOrb";

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
  scanResult: ScanResult | null;
  sseEvents: SSEProgressEvent[];
  currentStage: string;
  scanStatus: ScanStatusMode;
  showResults: boolean;
  outcome: "secure" | "breach" | null;
  reasoning: string[];
  summary: AnalyticsSummary | null;
  resilience: ResilienceMetrics | null;
  toast: ToastState | null;
  setToast: (t: ToastState | null) => void;
  githubSession: string | null;
  handleScan: (path?: string) => Promise<void>;
  shipToGithub: () => Promise<void>;
  shipping: boolean;
  refreshMetrics: () => Promise<void>;
}

const ScanContext = createContext<ScanContextValue | null>(null);

export function ScanProvider({ children }: { children: ReactNode }) {
  const [phase, setPhase] = useState<AppPhase>("splash");
  const [activePage, setActivePage] = useState("war-room");
  const [repoPath, setRepoPath] = useState("");
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [sseEvents, setSseEvents] = useState<SSEProgressEvent[]>([]);
  const [currentStage, setCurrentStage] = useState("IDLE");
  const [scanStatus, setScanStatus] = useState<ScanStatusMode>("idle");
  const [showResults, setShowResults] = useState(false);
  const [outcome, setOutcome] = useState<"secure" | "breach" | null>(null);
  const [reasoning, setReasoning] = useState<string[]>([]);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [resilience, setResilience] = useState<ResilienceMetrics | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [githubSession, setGithubSession] = useState<string | null>(
    () => localStorage.getItem("github_session")
  );
  const [shipping, setShipping] = useState(false);
  const prevReasoning = useRef(0);

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
    const params = new URLSearchParams(window.location.search);
    const session = params.get("github_session");
    if (session) {
      localStorage.setItem("github_session", session);
      setGithubSession(session);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  useEffect(() => {
    if (reasoning.length > prevReasoning.current) {
      setToast({ message: "Autopsy decision logic updated", variant: "info" });
    }
    prevReasoning.current = reasoning.length;
  }, [reasoning]);

  const handleScan = useCallback(
    async (path?: string) => {
      const target = (path ?? repoPath).trim();
      if (!target) return;
      setRepoPath(target);
      setScanning(true);
      setScanResult(null);
      setSseEvents([]);
      setCurrentStage("CLONING");
      setScanStatus("scanning");
      setShowResults(false);
      setOutcome(null);
      setReasoning([]);
      setActivePage("war-room");

      try {
        await streamScan(target, (evt) => {
          setSseEvents((prev) => [...prev, evt]);
          setCurrentStage(evt.stage);
          if (evt.ui_status) setScanStatus(evt.ui_status);
          if (evt.reasoning) setReasoning((r) => [...r, evt.reasoning!]);
          if (evt.status === "error") {
            setScanning(false);
            setScanStatus("breach");
            setToast({ message: evt.message, variant: "warning" });
          }
          if (evt.stage === "COMPLETE" && evt.status === "done" && evt.result) {
            setScanResult(evt.result);
            setScanning(false);
            setShowResults(true);
            setOutcome((evt.outcome as "secure" | "breach") || "breach");
            setScanStatus((evt.outcome as ScanStatusMode) || "breach");
            refreshMetrics();
          }
        });
      } catch (err) {
        setToast({ message: parseScanError(err), variant: "warning" });
        setScanning(false);
        setScanStatus("breach");
      }
    },
    [repoPath, refreshMetrics]
  );

  const shipToGithub = useCallback(async () => {
    if (!githubSession || !scanResult) {
      setToast({ message: "Unauthorized — login with GitHub first.", variant: "warning" });
      return;
    }
    setShipping(true);
    try {
      const name = `codesentinel-${scanResult.scan_id.toLowerCase()}`;
      const res = await api.shipToGithub(githubSession, {
        repo_name: name,
        local_path: scanResult.repo_path,
      });
      setToast({ message: `Deployed to ${res.repo_url}`, variant: "success" });
    } catch (err) {
      setToast({ message: parseScanError(err), variant: "warning" });
    } finally {
      setShipping(false);
    }
  }, [githubSession, scanResult]);

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
        scanResult,
        sseEvents,
        currentStage,
        scanStatus,
        showResults,
        outcome,
        reasoning,
        summary,
        resilience,
        toast,
        setToast,
        githubSession,
        handleScan,
        shipToGithub,
        shipping,
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
