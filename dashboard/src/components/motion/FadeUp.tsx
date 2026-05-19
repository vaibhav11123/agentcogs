import type { ReactNode } from "react";
import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";
import { MOTION_DISTANCE, MOTION_DURATION, MOTION_EASE, MOTION_STAGGER } from "@/lib/motion";

interface FadeUpProps {
  children: ReactNode;
  className?: string;
  delay?: number;
}

export function FadeUp({ children, className, delay = 0 }: FadeUpProps) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, y: MOTION_DISTANCE.md }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: reduced ? 0 : MOTION_DURATION.slow,
        ease: MOTION_EASE,
        delay: reduced ? 0 : delay,
      }}
    >
      {children}
    </motion.div>
  );
}

interface FadeUpStaggerProps {
  children: ReactNode;
  className?: string;
}

export function FadeUpStagger({ children, className }: FadeUpStaggerProps) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: { staggerChildren: reduced ? 0 : MOTION_STAGGER },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

interface FadeUpItemProps {
  children: ReactNode;
  className?: string;
}

export function FadeUpItem({ children, className }: FadeUpItemProps) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      className={className}
      variants={{
        hidden: reduced ? { opacity: 1, y: 0 } : { opacity: 0, y: MOTION_DISTANCE.md },
        visible: {
          opacity: 1,
          y: 0,
          transition: { duration: MOTION_DURATION.slow, ease: MOTION_EASE },
        },
      }}
    >
      {children}
    </motion.div>
  );
}

interface PageTransitionProps {
  children: ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: MOTION_DISTANCE.sm }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        duration: reduced ? 0 : MOTION_DURATION.normal,
        ease: MOTION_EASE,
      }}
    >
      {children}
    </motion.div>
  );
}
