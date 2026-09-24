import React, { useState } from 'react';
import { ArrowLeft, Sparkles, Scale, RefreshCw, Crown } from 'lucide-react';
import ScoreGauge from './ScoreGauge';
import ScoreBreakdown from './ScoreBreakdown';
import RecommendationsList from './RecommendationsList';
import ProPaywallStub from './ProPaywallStub';
import ResumeOptimizerModal from './ResumeOptimizerModal';
import { useAuth } from '../context/AuthContext';

export default function ResultsScreen({
  result,
  fileName,
  onReset,
  onOpenUpgrade
}) {
  const { isPro } = useAuth();
  const [isOptimizerModalOpen, setIsOptimizerModalOpen] = useState(false);

  const {
    ats_score = 0,
    breakdown = {},
    recommendations = [],
    engine = 'rubric_fallback',
    agent_engines = {},
    parsed_summary = {}
  } = result || {};

  // Track which recommendations are selected by the user to apply to their resume
  const [selectedFixes, setSelectedFixes] = useState(() => {
    return new Set(recommendations.map((_, i) => i));
  });

  const handleToggleFix = (index) => {
    setSelectedFixes((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  const isGemini = engine === 'gemini';

  return (
    <div className="w-full max-w-4xl mx-auto space-y-8 animate-fadeIn">
      {/* Top Bar: Back Action & Engine Attribution Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-brand-600 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Scan another resume</span>
        </button>

        {/* Engine Attribution Badge */}
        <div className="flex items-center gap-2">
          {isGemini ? (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-brand-100 text-brand-800 border border-brand-200 shadow-sm">
              <Sparkles className="w-3.5 h-3.5 text-brand-600" />
              <span>Scored via Gemini</span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 shadow-sm">
              <Scale className="w-3.5 h-3.5 text-slate-500" />
              <span>Scored via rubric fallback</span>
            </div>
          )}

          {/* Subtext indicator for agent breakdown */}
          <span className="text-[11px] text-slate-400 hidden md:inline">
            (P: {agent_engines.parser ? 'AI' : 'Rule'} • JD: {agent_engines.jd === null ? 'N/A' : agent_engines.jd ? 'AI' : 'Rule'} • R: {agent_engines.recommendation ? 'AI' : 'Rule'})
          </span>
        </div>
      </div>

      {/* Main Score Hero Card */}
      <div className="bg-white rounded-3xl p-8 sm:p-10 border border-slate-200 shadow-card flex flex-col md:flex-row items-center gap-8 justify-around">
        <ScoreGauge score={ats_score} />

        <div className="max-w-md text-center md:text-left">
          <div className="flex items-center justify-center md:justify-start gap-2 mb-2">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">
              Evaluation Target
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">
            {fileName || "Uploaded Resume"}
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 leading-relaxed mb-4">
            {ats_score >= 75
              ? "Your resume shows strong alignment with ATS formatting and content standards. Review the top recommendations below to refine high-impact bullet metrics."
              : ats_score >= 50
              ? "Your resume has a solid structural baseline, but certain formatting habits or missing keywords are reducing your interview callback potential."
              : "Significant ATS hazards detected (such as layout formatting, missing standard section titles, or low keyword density). Applying the fixes below will dramatically increase your match score."}
          </p>

          <div className="flex flex-wrap gap-2 justify-center md:justify-start text-[11px] text-slate-500 font-medium">
            <span className="px-2.5 py-1 rounded-lg bg-slate-100">
              {parsed_summary.skills_detected || 0} Skills Indexed
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-100">
              {parsed_summary.experience_entries || 0} Experience Blocks
            </span>
            <span className="px-2.5 py-1 rounded-lg bg-slate-100">
              {parsed_summary.has_jd ? "Targeted JD Analyzed" : "Universal ATS Benchmark"}
            </span>
          </div>
        </div>
      </div>

      {/* Category Breakdown (Keywords, Formatting, Sections, Achievements) */}
      <ScoreBreakdown
        breakdown={breakdown}
        hasJd={parsed_summary.has_jd}
      />

      {/* Recommendations Section */}
      <div className="space-y-6">
        {/* Full or Top 3 Recommendations based on Pro Status */}
        <RecommendationsList
          recommendations={recommendations}
          isPro={isPro}
          selectedFixes={selectedFixes}
          onToggleFix={handleToggleFix}
          onOpenUpgrade={onOpenUpgrade}
        />

        {/* Pro Locked Recommendations Stub (Only rendered for non-Pro users) */}
        {!isPro ? (
          <ProPaywallStub
            recommendations={recommendations}
            onOpenUpgrade={onOpenUpgrade}
          />
        ) : (
          /* Pro Active Next-Step Action Banner */
          <div className="p-6 bg-gradient-to-r from-amber-500/10 via-brand-500/10 to-sky-500/10 border border-amber-300/70 rounded-3xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-soft animate-fadeIn">
            <div className="flex items-center gap-3.5">
              <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-amber-500 to-amber-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs">
                <Crown className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <span>ResumeFit Pro Active</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-extrabold border border-amber-200">
                    All {recommendations.length} Fixes Unlocked
                  </span>
                </h4>
                <p className="text-xs text-slate-600 mt-0.5">
                  {selectedFixes.size} bullet {selectedFixes.size === 1 ? 'rewrite' : 'rewrites'} currently selected for your optimized resume.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setIsOptimizerModalOpen(true)}
              className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-2 transform hover:scale-[1.02]"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              <span>Generate Updated Resume</span>
            </button>
          </div>
        )}
      </div>

      {/* Auto-Optimizer & Export Modal */}
      <ResumeOptimizerModal
        isOpen={isOptimizerModalOpen}
        onClose={() => setIsOptimizerModalOpen(false)}
        result={result}
        selectedFixes={selectedFixes}
        fileName={fileName}
      />

      {/* Bottom Re-scan Action */}
      <div className="text-center pt-4 pb-8">
        <button
          onClick={onReset}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-xs font-semibold text-slate-600 bg-white hover:bg-slate-50 border border-slate-200 shadow-soft transition-colors"
        >
          <RefreshCw className="w-4 h-4 text-slate-400" />
          <span>Upload an updated revision or new resume</span>
        </button>
      </div>
    </div>
  );
}
