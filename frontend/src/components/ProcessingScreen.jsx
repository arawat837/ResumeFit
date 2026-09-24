import React, { useState, useEffect } from 'react';
import { CheckCircle2, Loader2, Sparkles, FileSearch, Target, BarChart3, Lightbulb, Server } from 'lucide-react';

export default function ProcessingScreen({ mode, isComplete, onFinishAnimation }) {
  // Step tracker: 0 = Parsing, 1 = JD, 2 = Scoring, 3 = Recommendations
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const steps = [
    {
      id: 0,
      title: 'Parsing Resume Structure',
      desc: 'Extracting contact information, skills, experience, and formatting cues...',
      icon: FileSearch,
    },
    {
      id: 1,
      title: mode === 'general' ? 'Benchmarking General ATS Standards' : 'Analyzing Job Description Criteria',
      desc: mode === 'general'
        ? 'Scanning core competency benchmarks & university hiring patterns...'
        : 'Extracting required skills, industry keywords, and seniority...',
      icon: Target,
    },
    {
      id: 2,
      title: 'Calculating ATS Rubric Score',
      desc: 'Checking keywords, section headers, formatting penalties, and quantified metrics...',
      icon: BarChart3,
    },
    {
      id: 3,
      title: 'Generating Actionable Fixes',
      desc: 'Prioritizing high-impact bullet edits and recommendations...',
      icon: Lightbulb,
    },
  ];

  useEffect(() => {
    // Progress through steps every 1.1 seconds while waiting for API
    const timer = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < 3) {
          return prev + 1;
        }
        return prev;
      });
    }, 1100);

    const elapsedTimer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);

    return () => {
      clearInterval(timer);
      clearInterval(elapsedTimer);
    };
  }, []);

  // When backend scan finishes, fast-forward to step 4 and trigger onFinishAnimation
  useEffect(() => {
    if (isComplete) {
      setCurrentStep(3);
      const finishTimeout = setTimeout(() => {
        onFinishAnimation();
      }, 700);
      return () => clearTimeout(finishTimeout);
    }
  }, [isComplete, onFinishAnimation]);

  return (
    <div className="w-full max-w-xl mx-auto bg-white rounded-3xl p-8 sm:p-10 border border-slate-200 shadow-card text-center animate-slideUp">
      {/* Top Animated Icon */}
      <div className="w-16 h-16 mx-auto rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mb-5 border border-brand-100 shadow-soft animate-pulse-subtle">
        <Sparkles className="w-8 h-8 stroke-[1.75]" />
      </div>

      <h2 className="text-xl font-bold text-slate-900 mb-2">
        Analyzing Your Resume
      </h2>
      <p className="text-sm text-slate-500 mb-6 max-w-md mx-auto">
        Our multi-agent pipeline is evaluating your resume against ATS tracking algorithms.
      </p>

      {/* Render Free-Tier Cold Start Banner (triggered if elapsed >= 10s) */}
      {elapsedSeconds >= 10 && !isComplete && (
        <div className="mb-6 p-4 rounded-2xl bg-amber-50/90 border border-amber-200/80 text-amber-900 flex items-start gap-3 text-left animate-fadeIn">
          <Server className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5 animate-pulse" />
          <div className="text-xs leading-relaxed">
            <p className="font-semibold text-amber-900 mb-0.5">
              Waking up the server
            </p>
            <p className="text-amber-800">
              Waking up the server — this can take up to a minute on the first request after inactivity.
            </p>
          </div>
        </div>
      )}

      {/* Steps List */}
      <div className="space-y-4 text-left">
        {steps.map((step) => {
          const StepIcon = step.icon;
          const isDone = currentStep > step.id || (isComplete && currentStep >= step.id);
          const isActive = currentStep === step.id && !isComplete;
          const isPending = currentStep < step.id;

          return (
            <div
              key={step.id}
              className={`p-4 rounded-2xl border transition-all duration-300 flex items-start gap-4 ${
                isActive
                  ? 'border-brand-300 bg-brand-50/70 shadow-sm scale-[1.01]'
                  : isDone
                  ? 'border-emerald-100 bg-emerald-50/40 text-slate-800'
                  : 'border-slate-100 bg-slate-50/50 opacity-50'
              }`}
            >
              {/* Status Indicator */}
              <div className="mt-0.5 flex-shrink-0">
                {isDone ? (
                  <div className="w-7 h-7 rounded-full bg-score-high/20 text-score-high flex items-center justify-center">
                    <CheckCircle2 className="w-4 h-4 stroke-[2.5]" />
                  </div>
                ) : isActive ? (
                  <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-600 flex items-center justify-center animate-spin">
                    <Loader2 className="w-4 h-4 stroke-[2.5]" />
                  </div>
                ) : (
                  <div className="w-7 h-7 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center">
                    <StepIcon className="w-3.5 h-3.5" />
                  </div>
                )}
              </div>

              {/* Step Info */}
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h4 className={`text-sm font-semibold ${
                    isActive ? 'text-brand-900' : isDone ? 'text-slate-900' : 'text-slate-500'
                  }`}>
                    {step.title}
                  </h4>
                  {isActive && (
                    <span className="text-[11px] font-medium text-brand-600 animate-pulse">
                      In progress...
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {step.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
