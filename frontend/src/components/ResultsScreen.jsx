import React, { useState } from 'react';
import { ArrowLeft, Sparkles, Scale, RefreshCw, Crown, AlertCircle } from 'lucide-react';
import ScoreGauge from './ScoreGauge';
import ScoreBreakdown from './ScoreBreakdown';
import RecommendationsList from './RecommendationsList';
import ProPaywallStub from './ProPaywallStub';
import ResumeOptimizerModal from './ResumeOptimizerModal';
import { useAuth } from '../context/AuthContext';
import { regenerateRecommendations } from '../services/api';

export default function ResultsScreen({
  result,
  fileName,
  onReset,
  onOpenUpgrade
}) {
  const { user, isPro } = useAuth();
  const [isOptimizerModalOpen, setIsOptimizerModalOpen] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [regenerateError, setRegenerateError] = useState(null);

  const {
    scan_id,
    ats_score = 0,
    breakdown = {},
    recommendations = [],
    engine = 'rubric_fallback',
    agent_engines = {},
    parsed_summary = {}
  } = result || {};

  const [currentRecommendations, setCurrentRecommendations] = useState(recommendations);
  const [currentEngine, setCurrentEngine] = useState(engine);
  const [currentAgentEngines, setCurrentAgentEngines] = useState(agent_engines);

  // Track which recommendations are selected by the user to apply to their resume
  const [selectedFixes, setSelectedFixes] = useState(() => {
    return new Set(currentRecommendations.map((_, i) => i));
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

  const handleRegenerate = async () => {
    if (!scan_id || isRegenerating) return;
    setIsRegenerating(true);
    setRegenerateError(null);
    try {
      const data = await regenerateRecommendations(scan_id);
      if (data && data.recommendations) {
        setCurrentRecommendations(data.recommendations);
        setSelectedFixes(new Set(data.recommendations.map((_, i) => i)));
        if (data.engine) setCurrentEngine(data.engine);
        if (data.agent_engines) setCurrentAgentEngines(data.agent_engines);
      }
    } catch (err) {
      console.error('Error regenerating recommendations:', err);
      setRegenerateError(err.message || 'Failed to regenerate recommendations. Please try again.');
    } finally {
      setIsRegenerating(false);
    }
  };

  const isGemini = currentEngine === 'gemini';


  return (
    <div className="w-full max-w-4xl mx-auto space-y-8 animate-fadeIn">
      {/* Top Bar: Back Action & Engine Attribution Badge */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div className="flex items-center gap-3">
          <button
            onClick={onReset}
            className="inline-flex items-center gap-2 text-xs font-semibold text-slate-600 hover:text-brand-600 transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Scan another resume</span>
          </button>

          {user && (
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                (user.scans_today || 0) >= (isPro ? 7 : 2)
                  ? 'bg-rose-50 text-rose-700 border border-rose-200'
                  : 'bg-slate-100 text-slate-600 border border-slate-200'
              }`}
            >
              <span>{`${user.scans_today || 0} of ${isPro ? 7 : 2} scans used today`}</span>
              {!isPro && (user.scans_today || 0) >= 2 && (
                <button
                  type="button"
                  onClick={onOpenUpgrade}
                  className="text-brand-600 font-semibold underline hover:text-brand-700 cursor-pointer ml-1"
                >
                  Upgrade to Pro
                </button>
              )}
            </span>
          )}
        </div>

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
            (P: {currentAgentEngines.parser ? 'AI' : currentAgentEngines.parser === null ? 'N/A' : 'Rule'} • JD: {currentAgentEngines.jd === null ? 'N/A' : currentAgentEngines.jd ? 'AI' : 'Rule'} • R: {currentAgentEngines.recommendation ? 'AI' : 'Rule'})
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
        {regenerateError && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2 animate-fadeIn">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{regenerateError}</span>
          </div>
        )}

        {/* Full or Top 3 Recommendations based on Pro Status */}
        <RecommendationsList
          recommendations={currentRecommendations}
          isPro={isPro}
          selectedFixes={selectedFixes}
          onToggleFix={handleToggleFix}
          onOpenUpgrade={onOpenUpgrade}
        />

        {/* Pro Locked Recommendations Stub (Only rendered for non-Pro users) */}
        {!isPro ? (
          <ProPaywallStub
            recommendations={currentRecommendations}
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
                    All {currentRecommendations.length} Fixes Unlocked
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
        result={{ ...result, recommendations: currentRecommendations }}
        selectedFixes={selectedFixes}
        fileName={fileName}
      />

      {/* Bottom Actions: Regenerate Recommendations & Re-scan */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4 pb-8">
        <button
          type="button"
          onClick={handleRegenerate}
          disabled={isRegenerating || !scan_id}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-xs font-bold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 shadow-soft transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          title="Re-run recommendation fixes using cached parse data without re-uploading"
        >
          <RefreshCw className={`w-4 h-4 text-brand-600 ${isRegenerating ? 'animate-spin' : ''}`} />
          <span>{isRegenerating ? 'Regenerating Recommendations...' : 'Regenerate Recommendations'}</span>
        </button>

        <button
          type="button"
          onClick={onReset}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-xs font-semibold text-slate-600 bg-white hover:bg-slate-50 border border-slate-200 shadow-soft transition-colors"
        >
          <ArrowLeft className="w-4 h-4 text-slate-400" />
          <span>Re-scan (upload updated file)</span>
        </button>
      </div>
    </div>
  );
}
