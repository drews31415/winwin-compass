"use client";

import { useEffect, useMemo, useState } from "react";

type RiskGaugeProps = {
  score: number;
  className?: string;
};

function clampScore(score: number) {
  return Math.max(0, Math.min(100, Number.isFinite(score) ? score : 0));
}

function riskLabel(score: number) {
  if (score < 40) return "낮음";
  if (score < 70) return "중간";
  return "높음";
}

function riskColor(score: number) {
  if (score < 40) return "#52B788";
  if (score < 70) return "#F4A261";
  return "#E63946";
}

export function RiskGauge({ score, className }: RiskGaugeProps) {
  const target = clampScore(score);
  const [displayScore, setDisplayScore] = useState(0);

  useEffect(() => {
    let frame = 0;
    const totalFrames = 36;
    const animate = () => {
      frame += 1;
      const progress = Math.min(frame / totalFrames, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayScore(Math.round(target * eased));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [target]);

  const arc = useMemo(() => {
    const radius = 82;
    const circumference = Math.PI * radius;
    const offset = circumference * (1 - target / 100);
    return { radius, circumference, offset };
  }, [target]);

  return (
    <div className={className}>
      <div className="relative mx-auto h-32 w-56">
        <svg viewBox="0 0 220 130" className="h-full w-full">
          <defs>
            <linearGradient id="risk-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#52B788" />
              <stop offset="50%" stopColor="#F4A261" />
              <stop offset="100%" stopColor="#E63946" />
            </linearGradient>
          </defs>
          <path
            d="M 28 110 A 82 82 0 0 1 192 110"
            fill="none"
            stroke="#E5E7EB"
            strokeLinecap="round"
            strokeWidth="18"
          />
          <path
            d="M 28 110 A 82 82 0 0 1 192 110"
            fill="none"
            stroke="url(#risk-gradient)"
            strokeDasharray={arc.circumference}
            strokeDashoffset={arc.offset}
            strokeLinecap="round"
            strokeWidth="18"
            className="transition-[stroke-dashoffset] duration-700"
          />
        </svg>
        <div className="absolute inset-x-0 bottom-0 text-center">
          <p className="text-4xl font-black" style={{ color: riskColor(target) }}>
            {displayScore}
          </p>
          <p className="text-sm font-semibold text-golmok-text-muted">위험도 {riskLabel(target)}</p>
        </div>
      </div>
    </div>
  );
}
