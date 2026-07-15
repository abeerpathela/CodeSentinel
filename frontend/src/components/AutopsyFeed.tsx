import { motion, AnimatePresence } from "framer-motion";

interface FeedEntry {
  timestamp: string;
  message: string;
  stage: string;
}

interface Props {
  feed: FeedEntry[];
  status: string;
  selfCorrection?: boolean;
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

function panelClass(status: string, selfCorrection: boolean): string {
  if (status === "error") return "border-red-500/50 shadow-glow-red";
  if (selfCorrection && status !== "complete") {
    return "border-orange-500/60 shadow-[0_0_24px_rgba(249,115,22,0.25)] animate-pulse";
  }
  if (status === "complete") {
    return "border-emerald-500/50 shadow-[0_0_24px_rgba(34,197,94,0.15)]";
  }
  return "";
}

export default function AutopsyFeed({ feed, status, selfCorrection = false }: Props) {
  const isCorrection = selfCorrection && status === "autopsy";
  const isVerified = status === "complete";

  return (
    <motion.div
      layout
      className={`cyber-panel flex h-full min-h-[520px] flex-col p-6 transition-colors duration-500 ${panelClass(status, selfCorrection)}`}
      animate={
        isCorrection
          ? { borderColor: "rgba(249,115,22,0.8)" }
          : isVerified
            ? { borderColor: "rgba(34,197,94,0.6)" }
            : {}
      }
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold tracking-wide">Agent Intelligence Feed</h2>
        <motion.span
          key={status}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className={`font-mono text-xs uppercase ${STAGE_COLORS[status] || "text-cyber-muted"}`}
        >
          {isCorrection ? "Correction in Progress" : isVerified ? "Verification Complete" : status}
        </motion.span>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto font-mono text-xs">
        <AnimatePresence mode="popLayout">
          {feed.length === 0 ? (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-cyber-muted"
            >
              Ready to stream Autopsy reasoning traces…
            </motion.p>
          ) : (
            feed.map((entry, i) => (
              <motion.div
                key={`${entry.timestamp}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25 }}
                className={`flex gap-2 border-l-2 pl-3 ${
                  entry.message.toLowerCase().includes("corrected")
                    ? "border-orange-500"
                    : "border-cyber-border"
                }`}
              >
                <span className="shrink-0 text-cyber-muted">
                  {new Date(entry.timestamp).toLocaleTimeString()}
                </span>
                <span className={STAGE_COLORS[entry.stage] || "text-cyber-text"}>
                  [{entry.stage}]
                </span>
                <span>{entry.message}</span>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
