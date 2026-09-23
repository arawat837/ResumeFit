import React from 'react';
import { X, Sparkles, Check, Download, RefreshCw, LayoutTemplate } from 'lucide-react';

export default function UpgradeModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  const proFeatures = [
    {
      title: 'Unlimited Scans & Re-scans',
      desc: 'Scan unlimited resume iterations as you apply to different companies and internships.',
      icon: RefreshCw,
    },
    {
      title: '1-Click "Generate Updated Resume"',
      desc: 'Automatically apply suggested edits and download a cleanly formatted, ATS-compliant DOCX or PDF.',
      icon: Download,
    },
    {
      title: 'Reference-Template Matching',
      desc: "Upload your college's required template, and ResumeFit will restructure your content to fit.",
      icon: LayoutTemplate,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 border border-slate-200 shadow-2xl relative animate-scaleUp">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-brand-100 text-brand-700">
            Phase 3 Roadmap Preview
          </span>
        </div>
        <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight mb-2">
          Upgrade to ResumeFit <span className="text-brand-600">Pro</span>
        </h3>
        <p className="text-xs sm:text-sm text-slate-500 mb-6">
          Everything you need to turn rejection emails into interview invitations. Built for university & MBA students.
        </p>

        {/* Feature Cards */}
        <div className="space-y-3 mb-6">
          {proFeatures.map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <div
                key={idx}
                className="p-3.5 rounded-xl border border-brand-100 bg-brand-50/40 flex items-start gap-3"
              >
                <div className="w-8 h-8 rounded-lg bg-brand-500 text-white flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs sm:text-sm font-bold text-slate-900">
                    {feat.title}
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                    {feat.desc}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Pricing & CTA */}
        <div className="pt-4 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <div className="flex items-baseline gap-1">
              <span className="text-2xl font-black text-slate-900">$4.99</span>
              <span className="text-xs text-slate-500 font-medium">/ month (student discount)</span>
            </div>
            <p className="text-[11px] text-slate-400">Cancel anytime • No long-term lock-in</p>
          </div>

          <button
            onClick={() => {
              alert("Payment integration is planned for Phase 3! Thanks for testing the ResumeFit prototype.");
              onClose();
            }}
            className="w-full sm:w-auto px-6 py-3 rounded-xl text-xs font-bold text-white bg-brand-600 hover:bg-brand-700 shadow-soft transition-all transform hover:scale-[1.02]"
          >
            Join Priority Waitlist
          </button>
        </div>
      </div>
    </div>
  );
}
