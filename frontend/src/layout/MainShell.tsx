import { AnimatePresence, motion } from "framer-motion";
import {
  Archive,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Network,
  Shield,
  Swords,
} from "lucide-react";
import { MiniOrbCanvas } from "../components/SentinelOrb";
import { useScan } from "../contexts/ScanContext";
import { sidebarItem } from "../lib/animations";
import ReportArchivePage from "../pages/ReportArchivePage";
import SecurityLabPage from "../pages/SecurityLabPage";
import SupplyChainPage from "../pages/SupplyChainPage";
import WarRoomPage from "../pages/WarRoomPage";

const NAV = [
  { id: "war-room", label: "Triage Center", icon: Swords },
  { id: "supply-chain", label: "Supply Chain Map", icon: Network },
  { id: "security-lab", label: "Security Lab", icon: FlaskConical },
  { id: "reports", label: "Report Archive", icon: Archive },
];

export default function MainShell() {
  const { activePage, setActivePage, setPhase, threatLevel, summary, resilience } = useScan();

  return (
    <div className="flex min-h-screen">
      <aside className="glass-sidebar fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-white/5 p-4 md:relative">
        <div className="mb-8 flex items-center gap-3 px-2">
          <MiniOrbCanvas threatLevel={threatLevel} />
          <div>
            <p className="font-mono text-[10px] uppercase tracking-widest text-cyber-accent">CodeSentinel</p>
            <p className="text-sm font-bold">Command Center</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {NAV.map(({ id, label, icon: Icon }) => (
            <motion.button
              key={id}
              type="button"
              variants={sidebarItem}
              initial="rest"
              whileHover="hover"
              onClick={() => setActivePage(id)}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-left text-sm transition ${
                activePage === id
                  ? "bg-cyan-500/15 text-cyan-300 shadow-glow"
                  : "text-cyber-muted hover:bg-white/5 hover:text-cyber-text"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </motion.button>
          ))}
        </nav>

        <div className="mt-auto space-y-3 border-t border-white/5 pt-4">
          {resilience && (
            <div className="rounded-xl bg-black/20 px-3 py-2 text-xs">
              <p className="text-cyber-muted">Resilience</p>
              <p className="font-mono text-lg font-bold text-cyan-400">{resilience.resilience_score}%</p>
            </div>
          )}
          {summary && (
            <p className="px-2 text-[10px] text-cyber-muted">
              {summary.total_scans} scans · {summary.total_vulnerabilities_caught} threats caught
            </p>
          )}
          <button
            type="button"
            onClick={() => setPhase("landing")}
            className="flex w-full items-center gap-2 rounded-xl px-4 py-2 text-xs text-cyber-muted hover:bg-white/5"
          >
            <LogOut className="h-3 w-3" />
            Exit to Landing
          </button>
        </div>
      </aside>

      <main className="flex-1 p-4 md:ml-0 md:p-8">
        <header className="mb-8 flex items-center gap-3">
          <LayoutDashboard className="h-5 w-5 text-cyber-accent" />
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-cyber-muted">
              Sentinel Mesh Active
            </p>
            <h1 className="text-xl font-bold">
              {NAV.find((n) => n.id === activePage)?.label || "Dashboard"}
            </h1>
          </div>
          <div className="ml-auto flex items-center gap-2 rounded-full border border-cyber-border px-3 py-1 text-xs">
            <Shield className="h-3 w-3 text-cyber-accent" />
            <span className="text-cyber-muted">Agent Mesh</span>
            <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
          </div>
        </header>

        <AnimatePresence mode="wait">
          <motion.div key={activePage}>
            {activePage === "war-room" && <WarRoomPage />}
            {activePage === "supply-chain" && <SupplyChainPage />}
            {activePage === "security-lab" && <SecurityLabPage />}
            {activePage === "reports" && <ReportArchivePage />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
