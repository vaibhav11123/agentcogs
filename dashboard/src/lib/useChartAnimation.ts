import { useEffect, useRef, useState } from "react";

const CHART_ANIMATION_MS = 600;

/** First paint only — subsequent data updates render instantly. */
export function useFirstChartAnimation(ready: boolean) {
  const hasPlayed = useRef(false);
  const [showAnimation, setShowAnimation] = useState(false);

  useEffect(() => {
    if (!ready || hasPlayed.current) return;

    setShowAnimation(true);
    const timer = setTimeout(() => {
      hasPlayed.current = true;
      setShowAnimation(false);
    }, CHART_ANIMATION_MS + 50);

    return () => clearTimeout(timer);
  }, [ready]);

  return showAnimation;
}

export const CHART_ANIMATION_DURATION = CHART_ANIMATION_MS;
