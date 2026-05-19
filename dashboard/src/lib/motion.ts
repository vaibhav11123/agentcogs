/** Baseline-style motion constants — decelerate, never bounce. */
export const MOTION_EASE = [0.16, 1, 0.3, 1] as const;

export const MOTION_DURATION = {
  fast: 0.12,
  normal: 0.2,
  slow: 0.4,
  counter: 0.8,
} as const;

export const MOTION_STAGGER = 0.05;

export const MOTION_DISTANCE = {
  sm: 4,
  md: 8,
} as const;
