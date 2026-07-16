import type { Finding, SBOMRisk } from "../lib/api";

interface Props {
  findings: Finding[];
  sbomRisks?: SBOMRisk[];
  warRoom?: boolean;
}

const SEV_ORDER = ["Critical", "High", "Medium", "Low"] as const;
const SEV_STYLES: Record<string, string> = {
  Critical: "border-red-500/60 bg-red-500/10 text-red-400",
  High: "border-red-400/50 bg-red-400/10 text-red-300",
  Medium: "border-amber-500/50 bg-amber-500/10 text-amber-300",
  Low: "border-cyber-border bg-cyber-bg/50 text-cyber-muted",
};

function normalizeSeverity(s: string): string {
  const cap = s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  return SEV_ORDER.includes(cap as (typeof SEV_ORDER)[number]) ? cap : "Low";
}

export default function ThreatHeatmap({ findings, sbomRisks = [], warRoom = false }: Props) {
  const combined = [
    ...findings.map((f) => ({
      id: f.file_path + f.vulnerability_type,
      label: f.file_path,
      type: f.vulnerability_type,
      severity: normalizeSeverity(f.severity),
      description: f.description,
      source: "code" as const,
    })),
    ...sbomRisks.map((r) => ({
      id: r.name + r.version,
      label: r.name,
      type: r.transitive_of ? `Transitive via ${r.transitive_of}` : "Direct dependency",
      severity: normalizeSeverity(r.risk_level),
      description: r.notes || "",
      source: "sbom" as const,
    })),
  ];

  const grouped = SEV_ORDER.map((sev) => ({
    severity: sev,
    items: combined.filter((c) => c.severity === sev),
  }));

  return (
    <div className={`cyber-panel p-6 ${warRoom && combined.length > 0 ? "animate-pulse border-red-500/30 shadow-glow-red" : ""}`}>
      <h2 className="mb-4 text-lg font-semibold tracking-wide">
        Threat Heatmap {warRoom && combined.length > 0 && <span className="text-red-400">⚠ WAR-ROOM</span>}
      </h2>
      {combined.length === 0 ? (
        <p className="text-sm text-cyber-muted">No threats detected. Run a scan to populate.</p>
      ) : (
        <div className="space-y-4">
          {grouped.map(
            (g) =>
              g.items.length > 0 && (
                <div key={g.severity}>
                  <div className="mb-2 flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 text-xs font-bold uppercase ${SEV_STYLES[g.severity]}`}
                    >
                      {g.severity}
                    </span>
                    <span className="text-xs text-cyber-muted">{g.items.length} finding(s)</span>
                  </div>
                  <ul className="space-y-2">
                    {g.items.map((item) => (
                      <li
                        key={item.id}
                        className={`rounded-lg border p-3 ${SEV_STYLES[item.severity]}`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-sm font-semibold">{item.label}</span>
                          <span className="text-xs uppercase opacity-70">{item.source}</span>
                        </div>
                        <p className="mt-1 text-xs opacity-80">{item.type}</p>
                        {item.description && (
                          <p className="mt-1 text-xs opacity-60">{item.description}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )
          )}
        </div>
      )}
    </div>
  );
}
