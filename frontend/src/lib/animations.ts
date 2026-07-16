import type { Transition, Variants } from "framer-motion";

export const pageTransition: Transition = {
  duration: 0.45,
  ease: [0.22, 1, 0.36, 1],
};

export const pageVariants: Variants = {
  initial: { opacity: 0, x: 24 },
  animate: { opacity: 1, x: 0, transition: pageTransition },
  exit: { opacity: 0, x: -16, transition: { duration: 0.3 } },
};

export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: { staggerChildren: 0.08, delayChildren: 0.06 },
  },
};

export const staggerItem: Variants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: pageTransition },
};

export const toastSpring = {
  type: "spring" as const,
  stiffness: 420,
  damping: 22,
  mass: 0.8,
};

export const toastVariants: Variants = {
  hidden: { opacity: 0, y: 80, scale: 0.6, rotate: -4 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    rotate: 0,
    transition: toastSpring,
  },
  exit: {
    opacity: 0,
    scale: 0.85,
    y: 20,
    transition: { duration: 0.2 },
  },
};

export const sidebarItem: Variants = {
  rest: { x: 0 },
  hover: { x: 4, transition: { duration: 0.2 } },
};
