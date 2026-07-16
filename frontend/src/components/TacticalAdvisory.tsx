import type { Finding, SBOMRisk } from "../lib/api";

interface Props {
  findings: Finding[];
  sbomRisks?: SBOMRisk[];
}

const SEV_ORDER = ["Critical", "High", "Medium", "Low"] as const;

const SEV_STYLES: Record<string, { border: string; badge: string; glow: string }> = {
  Critical: {
    border: "border-red-500/40",
    badge: "bg-red-500/15 text-red-400",
    glow: "shadow-glow-red",
  },
  High: {
    border: "border-orange-500/40",
    badge: "bg-orange-500/15 text-orange-400",
    glow: "shadow-glow-orange",
  },
  Medium: {
    border: "border-amber-500/30",
    badge: "bg-amber-500/10 text-amber-300",
    glow: "",
  },
  Low: {
    border: "border-emerald-500/20",
    badge: "bg-emerald-500/10 text-emerald-400",
    glow: "",
  },
};

function normalizeSeverity(s: string): string {
  const cap = s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  return SEV_ORDER.includes(cap as (typeof SEV_ORDER)[number]) ? cap : "Low";
}

export default function TacticalAdvisory({ findings, sbomRisks = [] }: Props) {
  const advisories = [
    ...findings.map((f, i) => ({
      id: `code-${i}-${f.file_path}`,
      severity: normalizeSeverity(f.severity),
      code: f.vulnerability_type,
      target: f.file_path,
      vector: "SOURCE",
      detail: f.description,
    })),
    ...sbomRisks.map((r, i) => ({
      id: `sbom-${i}-${r.name}`,
      severity: normalizeSeverity(r.risk_level),
      code: r.transitive_of ? `TRANSITIVE/${r.transitive_of}` : "SUPPLY_CHAIN",
      target: `${r.name}@${r.version}`,
      vector: "SBOM",
      detail: r.notes || "Dependency risk flagged by threat intelligence.",
    })),
  ];

  if (advisories.length === 0) {
    return (
      <div className="tactical-advisory">
        <div className="tactical-advisory-header">
          <span>SENTINEL ADVISORY FEED</span>
          <span className="text-emerald-400">CLEAR</span>
        </div>
        <p className="text-cyber-muted">No tactical advisories. Perimeter nominal.</p>
      </div>
    );
  }

  const grouped = SEV_ORDER.map((sev) => ({
    severity: sev,
    items: advisories.filter((a) => a.severity === sev),
  }));

  return (
    <div className="space-y-4 terminal-scroll max-h-[520px] overflow-y-auto pr-1">
      <div className="tactical-advisory-header px-1">
        <span>SENTINEL ADVISORY FEED</span>
        <span className="text-orange-400">{advisories.length} ACTIVE</span>
      </div>
      {grouped.map(
        (g) =>
          g.items.length > 0 && (
            <div key={g.severity} className="space-y-2">
              <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-cyber-muted">
                // {g.severity} tier — {g.items.length} signal(s)
              </p>
              {g.items.map((item) => {
                const style = SEV_STYLES[item.severity];
                return (
                  <article
                    key={item.id}
                    className={`tactical-advisory ${style.border} ${style.glow}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase ${style.badge}`}>
                        {item.severity}
                      </span>
                      <span className="text-[10px] uppercase tracking-widest text-cyber-muted">
                        {item.vector}
                      </span>
                    </div>
                    <p className="mt-2 text-emerald-400/90">
                      <span className="text-cyber-muted">SIG</span> {item.code}
                    </p>
                    <p className="mt-1 break-all text-cyber-text">{item.target}</p>
                    {item.detail && (
                      <p className="mt-2 border-t border-white/5 pt-2 text-xs leading-relaxed text-cyber-muted">
                        {item.detail}
                      </p>
                    )}
                  </article>
                );
              })}
            </div>
          )
      )}
    </div>
  );
}
