"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Animates from 0 to `target` once `active` becomes true (pair with
 * useInView so it fires on scroll-into-view, not on mount). Snaps straight
 * to the final value under prefers-reduced-motion.
 */
export function useCountUp(target: number, active: boolean, durationMs = 1100): number {
  const [value, setValue] = useState(0);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!active || startedRef.current) return;
    startedRef.current = true;

    if (typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setValue(target);
      return;
    }

    let raf: number;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - t, 3);
      setValue(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, target, durationMs]);

  return value;
}
