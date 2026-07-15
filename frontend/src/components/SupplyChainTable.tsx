import type { SBOMRisk } from "../lib/api";

interface Props {
  risks: SBOMRisk[];
}

function blastRadius(risk: SBOMRisk): number {
  const base: Record<string, number> = {
    Critical: 95,
    High: 75,
    Medium: 50,
    Low: 25,
  };
  let score = base[risk.risk_level] ?? 30;
  if (risk.transitive_of) score += 10;
  return Math.min(score, 100);
}

function radiusColor(score: number): string {
  if (score >= 85) return "text-red-400 bg-red-500/15 border-red-500/40";
  if (score >= 60) return "text-amber-400 bg-amber-500/15 border-amber-500/40";
  return "text-cyber-safe bg-emerald-500/10 border-emerald-500/30";
}

export default function SupplyChainTable({ risks }: Props) {
  if (risks.length === 0) {
    return (
      <div className="cyber-panel p-6">
        <h2 className="mb-2 text-lg font-semibold tracking-wide">Supply Chain Map</h2>
        <p className="text-sm text-cyber-muted">
          No SBOM risks detected. Dependency manifests will appear here after a scan.
        </p>
      </div>
    );
  }

  const sorted = [...risks].sort((a, b) => blastRadius(b) - blastRadius(a));

  return (
    <div className="cyber-panel overflow-hidden p-6">
      <h2 className="mb-4 text-lg font-semibold tracking-wide">Supply Chain Map</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-cyber-border text-xs uppercase tracking-wider text-cyber-muted">
              <th className="pb-3 pr-4">Package</th>
              <th className="pb-3 pr-4">Version</th>
              <th className="pb-3 pr-4">Risk</th>
              <th className="pb-3 pr-4">Transitive Via</th>
              <th className="pb-3">Blast Radius</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((risk) => {
              const score = blastRadius(risk);
              return (
                <tr key={`${risk.name}-${risk.version}`} className="border-b border-cyber-border/50">
                  <td className="py-3 pr-4 font-mono">{risk.name}</td>
                  <td className="py-3 pr-4 font-mono text-cyber-muted">{risk.version}</td>
                  <td className="py-3 pr-4">{risk.risk_level}</td>
                  <td className="py-3 pr-4 text-cyber-muted">{risk.transitive_of || "—"}</td>
                  <td className="py-3">
                    <span
                      className={`inline-flex min-w-[3rem] items-center justify-center rounded border px-2 py-1 font-mono text-xs font-bold ${radiusColor(score)}`}
                    >
                      {score}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
