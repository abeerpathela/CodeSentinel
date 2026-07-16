import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Bomb, FlaskConical, Package, Zap } from "lucide-react";
import { api, type RedTeamFixture } from "../lib/api";
import { useScan } from "../contexts/ScanContext";
import { pageVariants, staggerContainer, staggerItem } from "../lib/animations";

const ICONS: Record<string, typeof Bomb> = {
  supply_chain: Package,
  logic_bomb: Bomb,
  complex_rce: Zap,
};

export default function SecurityLabPage() {
  const { handleScan, scanning } = useScan();
  const [fixtures, setFixtures] = useState<RedTeamFixture[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .fixtures()
      .then(setFixtures)
      .catch(() => setFixtures([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" className="space-y-6">
      <div className="flex items-center gap-3">
        <FlaskConical className="h-8 w-8 text-cyber-accent" />
        <div>
          <h2 className="text-2xl font-bold">Security Lab</h2>
          <p className="text-sm text-cyber-muted">
            Red-Team fixtures — trigger demo scenarios against the Sentinel mesh.
          </p>
        </div>
      </div>

      {loading ? (
        <div className="glass-panel p-8 text-center text-cyber-muted">Loading fixtures…</div>
      ) : (
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"
        >
          {fixtures.map((fx) => {
            const Icon = ICONS[fx.id] || FlaskConical;
            return (
              <motion.div
                key={fx.id}
                variants={staggerItem}
                className="glass-panel flex flex-col p-6 transition hover:border-emerald-500/40"
              >
                <div className="mb-4 flex items-center gap-3">
                  <div className="rounded-lg bg-emerald-500/10 p-2">
                    <Icon className="h-5 w-5 text-cyber-accent" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{fx.name}</h3>
                    <p className="text-xs text-cyber-muted">{fx.category}</p>
                  </div>
                </div>
                <p className="mb-4 flex-1 text-sm text-cyber-muted">{fx.description}</p>
                <p className="mb-4 truncate font-mono text-[10px] text-cyber-muted">{fx.path}</p>
                <button
                  type="button"
                  className="cyber-btn w-full justify-center"
                  disabled={scanning}
                  onClick={() => handleScan(fx.path)}
                >
                  {scanning ? "Scanning…" : "Launch Red-Team Scan"}
                </button>
              </motion.div>
            );
          })}
        </motion.div>
      )}
    </motion.div>
  );
}
