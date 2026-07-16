import { motion } from "framer-motion";
import RiskGraph from "../components/RiskGraph";
import SupplyChainTable from "../components/SupplyChainTable";
import { useScan } from "../contexts/ScanContext";
import { pageVariants, staggerContainer, staggerItem } from "../lib/animations";

export default function SupplyChainPage() {
  const { scanResult } = useScan();
  const riskyNodes = (scanResult?.sbom_risks || []).map((r) => r.name);

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Supply Chain Map</h2>
        <p className="text-sm text-cyber-muted">
          SBOM dependency graph with transitive risk propagation and blast-radius scoring.
        </p>
      </div>
      {!scanResult ? (
        <div className="glass-panel p-12 text-center text-cyber-muted">
          Run a scan from Threat War-Room or Security Lab to populate the supply chain map.
        </div>
      ) : (
        <motion.div variants={staggerContainer} initial="initial" animate="animate" className="space-y-6">
          <motion.div variants={staggerItem}>
            <SupplyChainTable risks={scanResult.sbom_risks || []} />
          </motion.div>
          <motion.div variants={staggerItem}>
            <RiskGraph
              repoName={scanResult.repo_path?.split(/[/\\]/).pop() || "Repository"}
              edges={scanResult.sbom_graph || []}
              riskyNodes={riskyNodes}
            />
          </motion.div>
          {scanResult.sbom_assessment && (
            <motion.div variants={staggerItem} className="glass-panel p-6">
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-cyber-accent">
                Groq Threat Assessment
              </h3>
              <p className="text-sm text-cyber-muted">{scanResult.sbom_assessment}</p>
            </motion.div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}
