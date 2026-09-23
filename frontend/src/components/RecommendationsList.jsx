import React from 'react';
import { AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react';

export default function RecommendationsList({ recommendations }) {
  // Top 3 recommendations shown in full
  const topRecommendations = recommendations?.slice(0, 3) || [];

  return (
    <div className="w-full bg-white rounded-2xl p-6 border border-slate-200 shadow-soft">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
            Top Priority Action Items
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            The 3 most impactful edits to improve your ATS score
          </p>
        </div>
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          Free Included
        </span>
      </div>

      <div className="space-y-3.5">
        {topRecommendations.map((rec, index) => {
          const priority = rec.priority || index + 1;
          const isP1 = priority === 1;

          return (
            <div
              key={index}
              className={`p-4 rounded-xl border transition-all ${
                isP1
                  ? 'border-brand-200 bg-brand-50/40'
                  : 'border-slate-200 bg-white hover:bg-slate-50/50'
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-1.5">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-md text-[11px] font-bold ${
                      isP1
                        ? 'bg-brand-500 text-white'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    Priority {priority}
                  </span>
                  <h4 className="text-sm font-bold text-slate-900">
                    {rec.issue}
                  </h4>
                </div>
              </div>

              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed pl-0.5">
                {rec.suggestion}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
