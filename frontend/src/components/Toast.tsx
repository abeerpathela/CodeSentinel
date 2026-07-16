import { AnimatePresence, motion } from "framer-motion";
import { toastVariants } from "../lib/animations";

interface ToastProps {
  message: string;
  visible: boolean;
  variant?: "warning" | "success" | "info";
  onDismiss: () => void;
}

const VARIANT_STYLES = {
  warning: "border-orange-500/60 bg-orange-950/90 text-orange-200 shadow-[0_0_30px_rgba(249,115,22,0.3)]",
  success: "border-emerald-500/60 bg-emerald-950/90 text-emerald-200 shadow-[0_0_30px_rgba(34,197,94,0.25)]",
  info: "border-cyber-accent/60 bg-cyber-panel/95 text-cyber-text shadow-glow",
};

export default function Toast({ message, visible, variant = "info", onDismiss }: ToastProps) {
  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          variants={toastVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          className={`fixed bottom-6 right-6 z-[60] max-w-sm rounded-xl border px-5 py-4 backdrop-blur-md ${VARIANT_STYLES[variant]}`}
          role="alert"
        >
          <div className="flex items-start justify-between gap-3">
            <p className="text-sm font-semibold">{message}</p>
            <button
              type="button"
              onClick={onDismiss}
              className="shrink-0 text-xs opacity-60 hover:opacity-100"
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
