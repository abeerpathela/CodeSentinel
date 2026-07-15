interface GraphEdge {
  from: string;
  to: string;
  type?: string;
}

interface Props {
  repoName?: string;
  edges: GraphEdge[];
  riskyNodes?: string[];
}

const NODE_R = 28;

export default function RiskGraph({ repoName = "Your Repo", edges, riskyNodes = [] }: Props) {
  const nodes = new Map<string, { x: number; y: number; risky: boolean }>();
  nodes.set(repoName, { x: 120, y: 160, risky: false });

  const deps = new Set<string>();
  edges.forEach((e) => deps.add(e.to));
  const depList = Array.from(deps);
  depList.forEach((name, i) => {
    const angle = (i / Math.max(depList.length, 1)) * Math.PI * 1.2 + 0.3;
    const radius = 140;
    nodes.set(name, {
      x: 120 + Math.cos(angle) * radius + 180,
      y: 160 + Math.sin(angle) * radius,
      risky: riskyNodes.includes(name) || riskyNodes.some((r) => name.includes(r)),
    });
  });

  const nodeEntries = Array.from(nodes.entries());

  return (
    <div className="cyber-panel p-6">
      <h2 className="mb-4 text-lg font-semibold tracking-wide">Supply Chain Risk Graph</h2>
      {edges.length === 0 ? (
        <p className="text-sm text-cyber-muted">No dependency edges. SBOM manifests not found or no risks.</p>
      ) : (
        <svg viewBox="0 0 520 320" className="w-full" role="img" aria-label="Dependency risk graph">
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L6,3 L0,6 Z" fill="#475569" />
            </marker>
          </defs>
          {edges.map((edge, i) => {
            const from = nodes.get(edge.from) || nodes.get(repoName);
            const to = nodes.get(edge.to);
            if (!from || !to) return null;
            return (
              <line
                key={i}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
                stroke="#334155"
                strokeWidth="1.5"
                markerEnd="url(#arrow)"
              />
            );
          })}
          {nodeEntries.map(([name, pos]) => (
            <g key={name}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={NODE_R}
                fill={pos.risky ? "#ef444433" : "#22c55e33"}
                stroke={pos.risky ? "#ef4444" : "#22c55e"}
                strokeWidth="2"
              />
              <text
                x={pos.x}
                y={pos.y + NODE_R + 14}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="10"
                fontFamily="JetBrains Mono, monospace"
              >
                {name.length > 14 ? name.slice(0, 12) + "…" : name}
              </text>
            </g>
          ))}
        </svg>
      )}
      <div className="mt-3 flex gap-4 text-xs text-cyber-muted">
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-cyber-safe" /> Safe node
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block h-2 w-2 rounded-full bg-cyber-danger" /> Risky package
        </span>
      </div>
    </div>
  );
}
