import React, { useState } from 'react';
import { Sparkles, Crown, Check, Copy, CheckCircle2, ArrowRight, Zap, RefreshCw, Quote } from 'lucide-react';

export default function RecommendationsList({
  recommendations = [],
  isPro = false,
  selectedFixes = new Set(),
  onToggleFix,
  onOpenUpgrade
}) {
  const [copiedIndex, setCopiedIndex] = useState(null);

  // Free tier displays top 3; Pro tier displays all items (5-7)
  const visibleRecommendations = isPro
    ? recommendations
    : recommendations.slice(0, 3);

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    }).catch(() => {
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    });
  };

  const getPriorityStyle = (priority) => {
    if (priority === 1) {
      return {
        badge: 'bg-rose-50 text-rose-700 border-rose-200',
        card: 'border-brand-200 bg-brand-50/20'
      };
    }
    if (priority <= 3) {
      return {
        badge: 'bg-amber-50 text-amber-700 border-amber-200',
        card: 'border-slate-200 bg-white hover:bg-slate-50/40'
      };
    }
    return {
      badge: 'bg-blue-50 text-blue-700 border-blue-200',
      card: 'border-slate-200 bg-white hover:bg-slate-50/40'
    };
  };

  return (
    <div className="w-full bg-white rounded-3xl p-6 sm:p-8 border border-slate-200 shadow-soft space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-base font-bold text-slate-900">
              {isPro ? 'All Actionable Recommendations' : 'Top Priority Action Items'}
            </h3>
            {isPro ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                <Crown className="w-3 h-3 text-amber-600" />
                <span>Pro Unlocked ({recommendations.length} Fixes)</span>
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                Top 3 Free Included
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {isPro
              ? 'Every recommendation below is extracted directly from your resume bullets and sections.'
              : 'Grounded in your actual resume text. Upgrade to Pro to view and apply all recommendations.'}
          </p>
        </div>

        {isPro && (
          <div className="text-left sm:text-right">
            <span className="text-xs font-semibold text-slate-600">
              Selected for Auto-Optimizer:
            </span>
            <span className="ml-1.5 px-2.5 py-0.5 rounded-lg text-xs font-bold bg-brand-100 text-brand-700">
              {selectedFixes.size} / {recommendations.length}
            </span>
          </div>
        )}
      </div>

      {/* Recommendations Cards */}
      <div className="space-y-4">
        {visibleRecommendations.map((rec, index) => {
          const priority = rec.priority || index + 1;
          const styles = getPriorityStyle(priority);
          const isSelected = selectedFixes.has(index);
          const isCopied = copiedIndex === index;
          const hasRewrite = Boolean(rec.rewrite_bullet);

          return (
            <div
              key={index}
              className={`p-5 rounded-2xl border transition-all ${styles.card} ${
                isSelected && isPro ? 'ring-2 ring-brand-500/30' : ''
              }`}
            >
              {/* Card Header */}
              <div className="flex items-start justify-between gap-3 mb-2.5">
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className={`px-2.5 py-0.5 rounded-lg text-xs font-bold border ${styles.badge}`}>
                    Priority {priority}
                  </span>
                  <h4 className="text-sm font-bold text-slate-900">
                    {rec.issue}
                  </h4>
                  {rec.role && (
                    <span className="text-[11px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 font-medium">
                      {rec.role}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {/* Copy Suggestion or Rewrite Action */}
                  <button
                    type="button"
                    onClick={() => handleCopy(rec.rewrite_bullet || rec.suggestion, index)}
                    title="Copy to clipboard"
                    className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-1 text-[11px] font-medium"
                  >
                    {isCopied ? (
                      <>
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                        <span className="text-emerald-600 font-bold">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Copy</span>
                      </>
                    )}
                  </button>

                  {/* Pro Selection Checkbox */}
                  {isPro && onToggleFix && hasRewrite && (
                    <label className="flex items-center gap-1.5 cursor-pointer ml-1 bg-white px-2.5 py-1 rounded-lg border border-slate-200 hover:border-brand-400 transition-colors shadow-2xs">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleFix(index)}
                        className="w-3.5 h-3.5 rounded text-brand-600 focus:ring-brand-500 cursor-pointer"
                      />
                      <span className="text-[11px] font-bold text-slate-700 select-none">
                        Apply Rewrite
                      </span>
                    </label>
                  )}
                </div>
              </div>

              {/* Strategic Explanation */}
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed mb-3">
                {rec.suggestion}
              </p>

              {/* Concrete Before / After Bullet Diff (If this is a bullet rewrite) */}
              {hasRewrite && (
                <div className="mt-3 p-3.5 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-2 text-xs">
                  {rec.original_bullet && (
                    <div className="flex items-start gap-2 text-slate-500">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-slate-200 text-slate-700 flex-shrink-0">
                        Original
                      </span>
                      <p className="line-through italic">"{rec.original_bullet}"</p>
                    </div>
                  )}

                  <div className="flex items-start gap-2 text-emerald-800">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 flex-shrink-0 flex items-center gap-1">
                      <Sparkles className="w-2.5 h-2.5 text-emerald-600" />
                      <span>Google XYZ Rewrite</span>
                    </span>
                    <p className="font-semibold text-slate-800 leading-snug">
                      "{rec.rewrite_bullet}"
                    </p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
