import { motion } from "framer-motion";

interface Props {
  active: boolean;
}

export default function ScanLineOverlay({ active }: Props) {
  if (!active) return null;

  return (
    <div className="pointer-events-none fixed inset-0 z-40 overflow-hidden">
      <motion.div
        className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_20px_rgba(6,182,212,0.8)]"
        initial={{ top: "0%" }}
        animate={{ top: ["0%", "100%", "0%"] }}
        transition={{ duration: 3.5, repeat: Infinity, ease: "linear" }}
      />
      <div className="absolute inset-0 bg-cyan-500/[0.02]" />
    </div>
  );
}
