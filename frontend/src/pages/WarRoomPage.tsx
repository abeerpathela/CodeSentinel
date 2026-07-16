import { motion, AnimatePresence } from "framer-motion";
import AgentTerminal from "../components/AgentTerminal";
import ResilienceCounter from "../components/ResilienceCounter";
import ScanEngine from "../components/ScanEngine";
import ScanTimeline from "../components/ScanTimeline";
import SentinelOrb from "../components/SentinelOrb";
import ScanResults from "../views/ScanResults";
import { useScan } from "../contexts/ScanContext";
import { pageVariants, staggerContainer, staggerItem } from "../lib/animations";
import { API_BASE } from "../lib/api";

export default function WarRoomPage() {
  const {
    repoPath,
    setRepoPath,
    scanning,
    scanResult,
    sseEvents,
    currentStage,
    scanStatus,
    showResults,
    outcome,
    resilience,
    handleScan,
    shipToGithub,
    shipping,
    githubSession,
  } = useScan();

  const feed = sseEvents.map((e) => ({
    timestamp: e.timestamp,
    message: e.reasoning ? `${e.message} | ${e.reasoning}` : e.message,
    stage: e.stage.toLowerCase(),
  }));

  const cloning = currentStage === "CLONING" && scanning;

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Triage Center</h2>
          <p className="text-sm text-cyber-muted">Live SSE stream · Agent reasoning · 3D status orb</p>
        </div>
        <a
          href={`${API_BASE}/auth/login`}
          className="text-xs text-cyber-accent hover:underline"
        >
          {githubSession ? "GitHub connected" : "Login with GitHub"}
        </a>
      </div>

      <AnimatePresence mode="wait">
        {showResults && scanResult && outcome ? (
          <ScanResults
            key="results"
            result={scanResult}
            outcome={outcome}
            githubSession={githubSession}
            onShip={shipToGithub}
            shipping={shipping}
          />
        ) : (
          <motion.div
            key="live"
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="grid gap-6 xl:grid-cols-3"
          >
            <motion.div variants={staggerItem} className="xl:col-span-2 space-y-6">
              <div className="glass-panel overflow-hidden p-1">
                <SentinelOrb scanStatus={scanStatus} compact={false} className="h-64 md:h-80" />
              </div>
              <ScanEngine
                repoPath={repoPath}
                onChange={setRepoPath}
                onScan={() => handleScan()}
                scanning={scanning}
                cloning={cloning}
              />
              <ScanTimeline events={sseEvents} currentStage={currentStage} />
            </motion.div>
            <motion.div variants={staggerItem} className="space-y-6">
              {resilience && (
                <ResilienceCounter score={resilience.resilience_score} warRoom={scanning} />
              )}
              <AgentTerminal feed={feed} status={currentStage.toLowerCase()} />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
