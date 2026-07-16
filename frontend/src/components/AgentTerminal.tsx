import { useEffect, useRef, useState } from "react";
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
  cloning: "text-yellow-400",
  scanning: "text-cyber-accent",
  sbom: "text-purple-400",
  codebreaker: "text-amber-400",
  autopsy: "text-cyan-300",
  complete: "text-cyber-safe",
  error: "text-cyber-danger",
  queued: "text-cyber-muted",
};

function TypewriterLine({ text, color }: { text: string; color: string }) {
  const [display, setDisplay] = useState("");
  const idx = useRef(0);

  useEffect(() => {
    idx.current = 0;
    setDisplay("");
    const id = setInterval(() => {
      idx.current += 1;
      setDisplay(text.slice(0, idx.current));
      if (idx.current >= text.length) clearInterval(id);
    }, 12);
    return () => clearInterval(id);
  }, [text]);

  return (
    <span className={color}>
      {display}
      {display.length < text.length && <span className="animate-pulse">▌</span>}
    </span>
  );
}

export default function AgentTerminal({ feed, status, selfCorrection = false }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const isCorrection = selfCorrection && status === "autopsy";

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [feed]);

  return (
    <div
      className={`glass-panel flex h-full min-h-[480px] flex-col overflow-hidden ${
        isCorrection ? "border-orange-500/50 shadow-[0_0_24px_rgba(249,115,22,0.2)]" : ""
      }`}
    >
      <div className="flex items-center gap-2 border-b border-white/5 bg-black/30 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" />
        <span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
        <span className="ml-2 font-mono text-xs uppercase tracking-wider text-cyber-muted">
          Agent Reasoning Terminal
        </span>
        <span className={`ml-auto font-mono text-[10px] uppercase ${STAGE_COLORS[status] || ""}`}>
          {status}
        </span>
      </div>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto p-4 font-mono text-xs">
        <AnimatePresence mode="popLayout">
          {feed.length === 0 ? (
            <p className="text-cyber-muted">&gt; Awaiting agent mesh stream…</p>
          ) : (
            feed.map((entry, i) => {
              const isLatest = i === feed.length - 1;
              const line = `[${entry.stage}] ${entry.message}`;
              const color = STAGE_COLORS[entry.stage] || "text-cyber-text";
              return (
                <motion.div
                  key={`${entry.timestamp}-${i}`}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="border-l-2 border-cyan-500/30 pl-3"
                >
                  <span className="text-cyber-muted">
                    {new Date(entry.timestamp).toLocaleTimeString()}{" "}
                  </span>
                  {isLatest ? (
                    <TypewriterLine text={line} color={color} />
                  ) : (
                    <span className={color}>{line}</span>
                  )}
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
