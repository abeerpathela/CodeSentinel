interface FeedEntry {
  timestamp: string;
  message: string;
  stage: string;
}

interface Props {
  feed: FeedEntry[];
  status: string;
}

const STAGE_COLORS: Record<string, string> = {
  scanning: "text-cyber-accent",
  sbom: "text-purple-400",
  codebreaker: "text-amber-400",
  autopsy: "text-cyan-300",
  complete: "text-cyber-safe",
  error: "text-cyber-danger",
  queued: "text-cyber-muted",
};

export default function AutopsyFeed({ feed, status }: Props) {
  return (
    <div className="cyber-panel flex h-full flex-col p-6">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-wide">Autopsy Live-Feed</h2>
        <span className={`font-mono text-xs uppercase ${STAGE_COLORS[status] || "text-cyber-muted"}`}>
          {status}
        </span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto font-mono text-xs">
        {feed.length === 0 ? (
          <p className="text-cyber-muted">Waiting for agent activity...</p>
        ) : (
          feed.map((entry, i) => (
            <div key={i} className="flex gap-2 border-l-2 border-cyber-border pl-3">
              <span className="shrink-0 text-cyber-muted">
                {new Date(entry.timestamp).toLocaleTimeString()}
              </span>
              <span className={STAGE_COLORS[entry.stage] || "text-cyber-text"}>
                [{entry.stage}]
              </span>
              <span>{entry.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
