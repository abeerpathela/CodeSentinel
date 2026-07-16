interface Props {
  score: number;
  warRoom?: boolean;
}

export default function ResilienceCounter({ score, warRoom = false }: Props) {
  return (
    <div
      className={`cyber-panel flex flex-col items-center justify-center px-8 py-6 text-center ${
        warRoom ? "animate-pulse border-cyan-400/50 shadow-glow" : ""
      }`}
    >
      <p className="text-xs uppercase tracking-[0.25em] text-cyber-muted">
        National Resilience Score
      </p>
      <p
        className={`mt-2 font-mono text-5xl font-bold tabular-nums ${
          score >= 80 ? "text-emerald-400" : score >= 50 ? "text-amber-400" : "text-red-400"
        }`}
      >
        {score.toFixed(1)}%
      </p>
      <p className="mt-2 text-xs text-cyber-muted">
        Autopsy-corrected detection precision across all scans
      </p>
    </div>
  );
}
