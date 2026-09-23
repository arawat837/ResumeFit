import React from 'react';
import { Sparkles, FileCheck2 } from 'lucide-react';

export default function Header({ onOpenUpgrade }) {
  return (
    <header className="w-full bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-40 transition-all">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo & Tagline */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center text-white shadow-soft">
            <FileCheck2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-slate-900">
                Resume<span className="text-brand-600">Fit</span>
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-700">
                Student Beta
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Calm, explainable ATS scores & actionable recommendations
            </p>
          </div>
        </div>

        {/* Upgrade / Roadmap Trigger */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenUpgrade}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-brand-500" />
            <span>ResumeFit Pro</span>
          </button>
        </div>
      </div>
    </header>
  );
}
