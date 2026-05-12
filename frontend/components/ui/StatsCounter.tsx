"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  target: number;
  suffix?: string;
  duration?: number;
}

export function StatsCounter({ target, suffix = "", duration = 1400 }: Props) {
  const [count, setCount] = useState(0);
  const spanRef  = useRef<HTMLSpanElement>(null);
  const started  = useRef(false);

  useEffect(() => {
    const el = spanRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || started.current) return;
        started.current = true;

        const startTime = performance.now();
        const tick = (now: number) => {
          const elapsed  = now - startTime;
          const progress = Math.min(elapsed / duration, 1);
          // easeOut cubic
          const eased = 1 - Math.pow(1 - progress, 3);
          setCount(Math.round(eased * target));
          if (progress < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
      },
      { threshold: 0.6 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [target, duration]);

  return (
    <span ref={spanRef}>
      {count.toLocaleString("ko-KR")}
      {suffix}
    </span>
  );
}
