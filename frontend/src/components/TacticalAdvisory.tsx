import type { Finding, SBOMRisk } from "../lib/api";

interface Props {
  findings: Finding[];
  sbomRisks?: SBOMRisk[];
}

const SEV_ORDER = ["Critical", "High", "Medium", "Low"] as const;

const SEV_STYLES: Record<string, { border: string; badge: string; glow: string }> = {
  Critical: {
    border: "border-[#ff4b2b]/50",
    badge: "bg-[#ff4b2b]/15 text-[#ff4b2b]",
    glow: "shadow-glow-threat",
  },
  High: {
    border: "border-[#ff4b2b]/35",
    badge: "bg-[#ff4b2b]/10 text-[#ff8066]",
    glow: "shadow-glow-threat",
  },
  Medium: {
    border: "border-white/10",
    badge: "bg-white/5 text-cyber-text",
    glow: "",
  },
  Low: {
    border: "border-[#00ff41]/20",
    badge: "bg-[#00ff41]/10 text-[#00ff41]",
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
      vector: "SRC",
      detail: f.description,
    })),
    ...sbomRisks.map((r, i) => ({
      id: `sbom-${i}-${r.name}`,
      severity: normalizeSeverity(r.risk_level),
      code: r.transitive_of ? `TX/${r.transitive_of}` : "SUPPLY",
      target: `${r.name}@${r.version}`,
      vector: "SBOM",
      detail: r.notes || "Dependency risk flagged by threat intelligence.",
    })),
  ];

  if (advisories.length === 0) {
    return (
      <div className="tactical-advisory soc-feed">
        <div className="tactical-advisory-header">
          <span>SOC // TACTICAL FEED</span>
          <span className="text-[#00ff41]">NOMINAL</span>
        </div>
        <p className="text-cyber-muted">&gt; no active advisories</p>
      </div>
    );
  }

  const grouped = SEV_ORDER.map((sev) => ({
    severity: sev,
    items: advisories.filter((a) => a.severity === sev),
  }));

  return (
    <div className="space-y-3 terminal-scroll max-h-[520px] overflow-y-auto pr-1 soc-feed">
      <div className="tactical-advisory-header px-1">
        <span>SOC // TACTICAL FEED</span>
        <span className="text-[#ff4b2b]">{advisories.length} ALERT</span>
      </div>
      {grouped.map(
        (g) =>
          g.items.length > 0 && (
            <div key={g.severity} className="space-y-2">
              <p className="text-[10px] uppercase tracking-[0.35em] text-cyber-muted">
                [{g.severity}] {g.items.length} event(s)
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
                      <span className="text-[10px] tracking-widest text-cyber-muted">{item.vector}</span>
                    </div>
                    <p className="mt-2 text-[#00ff41]">
                      <span className="text-cyber-muted">&gt; SIG </span>
                      {item.code}
                    </p>
                    <p className="mt-1 break-all">{item.target}</p>
                    {item.detail && (
                      <p className="mt-2 border-t border-white/5 pt-2 text-xs text-cyber-muted">{item.detail}</p>
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
