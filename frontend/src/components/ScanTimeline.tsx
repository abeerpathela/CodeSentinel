import { motion } from "framer-motion";
import { Check, Circle, Loader2 } from "lucide-react";
import type { SSEProgressEvent } from "../lib/api";

const STAGES = ["CLONING", "PARSING", "SBOM", "CODEBREAKER", "AUTOPSY", "CLEANUP", "COMPLETE"] as const;

interface Props {
  events: SSEProgressEvent[];
  currentStage: string;
}

export default function ScanTimeline({ events, currentStage }: Props) {
  const completed = new Set(
    events.filter((e) => e.status === "done").map((e) => e.stage.toUpperCase())
  );
  const active = currentStage.toUpperCase();
  const errored = events.some((e) => e.status === "error");

  return (
    <div className="glass-panel p-6">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-cyber-accent">
        Live Scan Timeline
      </h3>
      <ol className="relative space-y-0 border-l border-cyber-border pl-6">
        {STAGES.map((stage, i) => {
          const isDone = completed.has(stage) || (stage === "COMPLETE" && completed.has("COMPLETE"));
          const isActive = active === stage && !isDone;
          const isPending = !isDone && !isActive;

          return (
            <motion.li
              key={stage}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="relative pb-6 last:pb-0"
            >
              <span
                className={`absolute -left-[1.85rem] flex h-6 w-6 items-center justify-center rounded-full border ${
                  isDone
                    ? "border-emerald-500/60 bg-emerald-500/20 text-emerald-400"
                    : isActive
                      ? "border-cyan-400/60 bg-cyan-500/20 text-cyan-300"
                      : "border-cyber-border bg-cyber-bg text-cyber-muted"
                }`}
              >
                {isDone ? (
                  <Check className="h-3 w-3" />
                ) : isActive ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Circle className="h-2 w-2" />
                )}
              </span>
              <p
                className={`text-xs font-semibold uppercase tracking-wide ${
                  isDone ? "text-emerald-400" : isActive ? "text-cyan-300" : "text-cyber-muted"
                }`}
              >
                {stage.replace("_", " ")}
              </p>
              <p className="text-[11px] text-cyber-muted">
                {(() => {
                  const stageEvents = events.filter((e) => e.stage.toUpperCase() === stage);
                  return stageEvents.length > 0
                    ? stageEvents[stageEvents.length - 1].message
                    : isPending
                      ? "Pending…"
                      : "";
                })()}
              </p>
            </motion.li>
          );
        })}
      </ol>
      {errored && (
        <p className="mt-3 text-xs text-red-400">Scan halted — see agent terminal for details.</p>
      )}
    </div>
  );
}
