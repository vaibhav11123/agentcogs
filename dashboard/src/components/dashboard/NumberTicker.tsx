"use client";

import { useEffect, useRef } from "react";
import { animate, useInView, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";
import { MOTION_DURATION, MOTION_EASE } from "@/lib/motion";

interface NumberTickerProps {
  value: number;
  className?: string;
  decimalPlaces?: number;
  prefix?: string;
  suffix?: string;
}

export function NumberTicker({
  value,
  className,
  decimalPlaces = 1,
  prefix = "",
  suffix = "",
}: NumberTickerProps) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true });
  const reduced = useReducedMotion();

  const format = (n: number) => `${prefix}${n.toFixed(decimalPlaces)}${suffix}`;

  useEffect(() => {
    if (!isInView || !ref.current) return;

    if (reduced) {
      ref.current.textContent = format(value);
      return;
    }

    const controls = animate(0, value, {
      duration: MOTION_DURATION.counter,
      ease: MOTION_EASE,
      onUpdate(latest) {
        if (ref.current) ref.current.textContent = format(latest);
      },
    });

    return () => controls.stop();
  }, [isInView, value, reduced, decimalPlaces, prefix, suffix]);

  return (
    <span ref={ref} className={cn("font-mono tabular-nums tracking-tight", className)}>
      {reduced ? format(value) : format(0)}
    </span>
  );
}
