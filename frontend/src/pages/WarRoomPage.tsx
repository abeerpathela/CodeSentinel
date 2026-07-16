import { motion } from "framer-motion";
import AgentTerminal from "../components/AgentTerminal";
import ResilienceCounter from "../components/ResilienceCounter";
import ScanEngine from "../components/ScanEngine";
import SentinelOrb from "../components/SentinelOrb";
import ThreatHeatmap from "../components/ThreatHeatmap";
import ThreatMatrix from "../components/ThreatMatrix";
import { useScan } from "../contexts/ScanContext";
import { pageVariants, staggerContainer, staggerItem } from "../lib/animations";

export default function WarRoomPage() {
  const {
    repoPath,
    setRepoPath,
    scanning,
    cloning,
    scanResult,
    feed,
    feedStatus,
    threatLevel,
    resilience,
    handleScan,
  } = useScan();

  const warRoom = threatLevel === "threat" || scanning || cloning;

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Triage Center</h2>
        <p className="text-sm text-cyber-muted">
          Real-time agent reasoning, threat matrix, and 3D status telemetry.
        </p>
      </div>
      <motion.div variants={staggerContainer} initial="initial" animate="animate" className="grid gap-6 xl:grid-cols-3">
        <motion.div variants={staggerItem} className="xl:col-span-2 space-y-6">
          <div className="glass-panel overflow-hidden p-1">
            <SentinelOrb threatLevel={threatLevel} compact={false} className="h-64 md:h-80" />
          </div>
          <ScanEngine
            repoPath={repoPath}
            onChange={setRepoPath}
            onScan={() => handleScan()}
            scanning={scanning}
            cloning={cloning}
          />
          <div className="grid gap-6 md:grid-cols-2">
            <ThreatMatrix
              findings={scanResult?.findings || []}
              sbomRisks={scanResult?.sbom_risks}
            />
            <ThreatHeatmap
              findings={scanResult?.findings || []}
              sbomRisks={scanResult?.sbom_risks}
              warRoom={warRoom}
            />
          </div>
        </motion.div>
        <motion.div variants={staggerItem} className="space-y-6">
          {resilience && <ResilienceCounter score={resilience.resilience_score} warRoom={warRoom} />}
          <AgentTerminal
            feed={feed}
            status={feedStatus}
            selfCorrection={
              scanResult?.self_correction_triggered ||
              feed.some((f) => f.message.toLowerCase().includes("corrected"))
            }
          />
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
