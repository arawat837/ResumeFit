import React from 'react';
import { Lock, Sparkles, ArrowRight } from 'lucide-react';

export default function ProPaywallStub({ recommendations, onOpenUpgrade }) {
  // Items beyond the top 3
  const lockedItems = recommendations?.slice(3) || [];
  const lockedCount = lockedItems.length;

  return (
    <div className="w-full relative rounded-2xl border border-brand-200 bg-white shadow-soft overflow-hidden">
      {/* Blurred Dummy Content Behind */}
      <div className="p-6 filter blur-[5px] opacity-40 select-none pointer-events-none space-y-4">
        {lockedItems.map((item, idx) => (
          <div key={idx} className="p-4 rounded-xl border border-slate-200 bg-slate-50">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-slate-200 text-slate-700">
                Priority {idx + 4}
              </span>
              <h4 className="text-sm font-bold text-slate-900 truncate">
                {item.issue || "Advanced keyword and phrasing alignment"}
              </h4>
            </div>
            <p className="text-xs text-slate-600 line-clamp-2">
              {item.suggestion || "Detailed structural line-by-line rewrite suggestions..."}
            </p>
          </div>
        ))}
      </div>

      {/* Frosted Glass Overlay with Upgrade CTA */}
      <div className="absolute inset-0 bg-gradient-to-t from-white via-white/80 to-transparent flex flex-col items-center justify-center p-6 text-center">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-brand-500 to-brand-400 text-white flex items-center justify-center mb-3 shadow-soft">
          <Lock className="w-5 h-5 stroke-[2]" />
        </div>

        <h4 className="text-base font-bold text-slate-900 mb-1">
          +{lockedCount} More Personalized Suggestions
        </h4>
        <p className="text-xs text-slate-500 max-w-sm mb-4">
          Unlock the full diagnostic checklist, line-by-line bullet rewrites, and target formatting insights with ResumeFit Pro.
        </p>

        <button
          type="button"
          onClick={onOpenUpgrade}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-brand-600 hover:bg-brand-700 shadow-soft transition-all transform hover:scale-[1.02]"
        >
          <Sparkles className="w-4 h-4 text-brand-200" />
          <span>Unlock with ResumeFit Pro</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
