import { motion } from "framer-motion";
import { ArrowRight, Shield } from "lucide-react";
import SentinelOrb from "../components/SentinelOrb";
import ResilienceCounter from "../components/ResilienceCounter";
import { useScan } from "../contexts/ScanContext";
import { staggerContainer, staggerItem } from "../lib/animations";

export default function LandingPage() {
  const { setPhase, threatLevel, resilience } = useScan();

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 py-12">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(6,182,212,0.15),transparent_60%)]" />
      <motion.div
        variants={staggerContainer}
        initial="initial"
        animate="animate"
        className="relative z-10 grid w-full max-w-6xl gap-10 lg:grid-cols-2 lg:items-center"
      >
        <motion.div variants={staggerItem} className="space-y-6">
          <p className="font-mono text-xs uppercase tracking-[0.4em] text-cyber-accent">
            Enterprise Security Suite
          </p>
          <h1 className="bg-gradient-to-br from-cyan-200 via-white to-slate-400 bg-clip-text text-5xl font-bold leading-tight text-transparent">
            Sentinel Command Center
          </h1>
          <p className="max-w-lg text-lg text-cyber-muted">
            Immersive agentic defense for supply-chain threats. Scan local repos or public
            GitHub URLs — Codebreaker analyzes, Autopsy self-corrects, SBOM maps your surface.
          </p>
          <div className="flex flex-wrap gap-4">
            <button
              type="button"
              onClick={() => setPhase("command")}
              className="cyber-btn group text-base"
            >
              <Shield className="h-5 w-5" />
              Enter Command Center
              <ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" />
            </button>
          </div>
          {resilience && (
            <div className="max-w-xs">
              <ResilienceCounter score={resilience.resilience_score} />
            </div>
          )}
        </motion.div>
        <motion.div variants={staggerItem}>
          <div className="glass-panel p-2">
            <SentinelOrb threatLevel={threatLevel} />
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}
