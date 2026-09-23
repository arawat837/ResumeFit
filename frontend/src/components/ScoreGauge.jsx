import React, { useEffect, useState } from 'react';

export default function ScoreGauge({ score }) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const duration = 1200;
    const steps = 40;
    const increment = score / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += increment;
      if (current >= score) {
        setAnimatedScore(score);
        clearInterval(timer);
      } else {
        setAnimatedScore(Math.round(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [score]);

  // Determine color and friendly message
  let color = '#38BDF8'; // primary sky blue
  let badgeText = 'Strong Match';
  let badgeBg = 'bg-brand-100 text-brand-800 border-brand-200';

  if (score >= 75) {
    color = '#22C55E';
    badgeText = 'Strong ATS Compatibility';
    badgeBg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (score >= 50) {
    color = '#F59E0B';
    badgeText = 'Good Foundation — Needs Targeted Edits';
    badgeBg = 'bg-amber-50 text-amber-700 border-amber-200';
  } else {
    color = '#EF4444';
    badgeText = 'Needs Formatting & Keyword Attention';
    badgeBg = 'bg-rose-50 text-rose-700 border-rose-200';
  }

  // SVG Gauge calculations
  const size = 180;
  const strokeWidth = 14;
  const center = size / 2;
  const radius = center - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg className="w-full h-full transform -rotate-90" viewBox={`0 0 ${size} ${size}`}>
          {/* Background track */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            stroke="#E0F2FE"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Animated score ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            style={{ transition: 'stroke-dashoffset 0.8s ease-out' }}
          />
        </svg>

        {/* Center Text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-4xl font-extrabold text-slate-900 tracking-tight">
            {animatedScore}
          </span>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest mt-0.5">
            / 100
          </span>
        </div>
      </div>

      {/* Status Badge */}
      <div className={`mt-4 px-3.5 py-1 rounded-full text-xs font-semibold border ${badgeBg} shadow-sm`}>
        {badgeText}
      </div>
    </div>
  );
}
