import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import type { Finding, SBOMRisk } from "../lib/api";

interface Props {
  findings: Finding[];
  sbomRisks?: SBOMRisk[];
}

const LEVELS = [
  { key: "Critical", color: "bg-red-500", glow: "shadow-[0_0_12px_rgba(239,68,68,0.6)]" },
  { key: "High", color: "bg-orange-500", glow: "shadow-[0_0_10px_rgba(249,115,22,0.5)]" },
  { key: "Medium", color: "bg-amber-400", glow: "" },
  { key: "Low", color: "bg-emerald-600", glow: "" },
];

function norm(s: string) {
  const c = s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  return LEVELS.some((l) => l.key === c) ? c : "Low";
}

export default function ThreatMatrix({ findings, sbomRisks = [] }: Props) {
  const counts: Record<string, number> = { Critical: 0, High: 0, Medium: 0, Low: 0 };
  findings.forEach((f) => {
    counts[norm(f.severity)] += 1;
  });
  sbomRisks.forEach((r) => {
    counts[norm(r.risk_level)] += 1;
  });
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const max = Math.max(...Object.values(counts), 1);

  return (
    <div className="glass-panel p-6">
      <h2 className="mb-1 text-lg font-semibold tracking-wide">Threat Matrix</h2>
      <p className="mb-4 text-xs text-cyber-muted">Severity distribution across code + SBOM</p>
      {total === 0 ? (
        <p className="text-sm text-cyber-muted">No threats in current scan.</p>
      ) : (
        <div className="space-y-3">
          {LEVELS.map(({ key, color, glow }) => {
            const n = counts[key];
            const pct = (n / max) * 100;
            return (
              <div key={key}>
                <div className="mb-1 flex justify-between font-mono text-xs">
                  <span className="text-cyber-muted">{key}</span>
                  <span>{n}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-cyber-border">
                  <motion.div
                    className={`h-full rounded-full ${color} ${glow}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ duration: 0.6, ease: "easeOut" }}
                  />
                </div>
              </div>
            );
          })}
          <p className="pt-2 text-center font-mono text-xs text-cyber-accent">
            {total} total threat signal{total !== 1 ? "s" : ""}
          </p>
        </div>
      )}
    </div>
  );
}
