import { motion } from "framer-motion";
import AutopsyFeed from "../components/AutopsyFeed";
import ResilienceCounter from "../components/ResilienceCounter";
import ScanEngine from "../components/ScanEngine";
import SentinelOrb from "../components/SentinelOrb";
import ThreatHeatmap from "../components/ThreatHeatmap";
import { useScan } from "../contexts/ScanContext";
import { pageVariants, staggerContainer, staggerItem } from "../lib/animations";

export default function WarRoomPage() {
  const {
    repoPath,
    setRepoPath,
    scanning,
    scanResult,
    feed,
    feedStatus,
    threatLevel,
    resilience,
    handleScan,
  } = useScan();

  const warRoom = threatLevel === "threat" || scanning;

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
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
          />
          <ThreatHeatmap
            findings={scanResult?.findings || []}
            sbomRisks={scanResult?.sbom_risks}
            warRoom={warRoom}
          />
        </motion.div>
        <motion.div variants={staggerItem}>
          {resilience && <ResilienceCounter score={resilience.resilience_score} warRoom={warRoom} />}
          <div className="mt-6 min-h-[480px]">
            <AutopsyFeed
              feed={feed}
              status={feedStatus}
              selfCorrection={
                scanResult?.self_correction_triggered ||
                feed.some((f) => f.message.toLowerCase().includes("corrected"))
              }
            />
          </div>
        </motion.div>
      </motion.div>
    </motion.div>
  );
}
