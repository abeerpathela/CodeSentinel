import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import SentinelOrb from "./SentinelOrb";

interface Props {
  onComplete: () => void;
}

const STEPS = [
  "Initializing Sentinel Mesh…",
  "Loading Codebreaker (Gemini)…",
  "Arming Autopsy Auditor (Groq)…",
  "Syncing ChromaDB Memory…",
  "Calibrating SBOM Engine…",
  "Command Center Ready",
];

export default function SplashScreen({ onComplete }: Props) {
  const [progress, setProgress] = useState(0);
  const [stepIdx, setStepIdx] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((p) => {
        const next = Math.min(p + 2.2, 100);
        const idx = Math.min(Math.floor(next / (100 / STEPS.length)), STEPS.length - 1);
        setStepIdx(idx);
        if (next >= 100) {
          clearInterval(interval);
          setTimeout(onComplete, 600);
        }
        return next;
      });
    }, 55);
    return () => clearInterval(interval);
  }, [onComplete]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-cyber-bg">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(6,182,212,0.12),transparent_70%)]" />
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative z-10 w-full max-w-lg px-8 text-center"
      >
        <div className="mx-auto mb-8 h-40 w-40">
          <SentinelOrb scanStatus="scanning" compact className="h-full" />
        </div>
        <p className="font-mono text-xs uppercase tracking-[0.4em] text-cyber-accent">CodeSentinel</p>
        <h1 className="mt-2 text-2xl font-bold text-cyber-text">Sentinel Command Center</h1>
        <p className="mt-4 font-mono text-sm text-cyber-muted">{STEPS[stepIdx]}</p>
        <div className="mt-8 h-1.5 overflow-hidden rounded-full bg-cyber-border">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-orange-400"
            style={{ width: `${progress}%` }}
            layout
          />
        </div>
        <p className="mt-2 font-mono text-xs text-cyber-muted">{Math.round(progress)}%</p>
      </motion.div>
    </div>
  );
}
