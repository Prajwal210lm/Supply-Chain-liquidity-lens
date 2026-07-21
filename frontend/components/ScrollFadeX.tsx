"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

// Wraps a horizontally-scrollable element and shows a right-edge fade
// whenever there is more content to scroll to. The fade tracks scroll
// position (it hides once the user reaches the end) and re-checks on
// resize, so it never falsely hints at scroll when content already fits.
export default function ScrollFadeX({
  children,
  className = "",
  fadeClassName = "",
  wrapperClassName = "relative",
}: {
  children: ReactNode;
  className?: string;
  fadeClassName?: string;
  wrapperClassName?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [showFade, setShowFade] = useState(false);

  const check = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const hasOverflow = el.scrollWidth - el.clientWidth > 2;
    const atEnd = el.scrollLeft >= el.scrollWidth - el.clientWidth - 2;
    setShowFade(hasOverflow && !atEnd);
  }, []);

  useEffect(() => {
    check();
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(check);
    ro.observe(el);
    el.addEventListener("scroll", check, { passive: true });
    window.addEventListener("resize", check);
    return () => {
      ro.disconnect();
      el.removeEventListener("scroll", check);
      window.removeEventListener("resize", check);
    };
  }, [check]);

  return (
    <div className={wrapperClassName}>
      <div ref={ref} className={className}>
        {children}
      </div>
      <div
        aria-hidden="true"
        className={`pointer-events-none absolute top-0 right-0 bottom-0 w-10 transition-opacity duration-200 ${fadeClassName} ${
          showFade ? "opacity-100" : "opacity-0"
        }`}
        style={{ background: "linear-gradient(to left, var(--card), transparent)" }}
      />
    </div>
  );
}
