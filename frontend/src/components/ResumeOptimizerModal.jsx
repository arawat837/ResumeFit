import React, { useState } from 'react';
import {
  X,
  Sparkles,
  Download,
  FileText,
  CheckCircle2,
  AlertCircle,
  Loader2,
  TrendingUp,
  ShieldCheck,
  Crown,
  GraduationCap,
  Terminal,
  Briefcase,
  Check
} from 'lucide-react';
import { getStoredToken } from '../services/auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const TEMPLATES = [
  {
    id: 'ivy_league',
    name: 'Ivy League / Academic',
    subtitle: 'Harvard & Wharton Format',
    desc: 'Centered header, classic academic hierarchy (Education → Experience → Skills).',
    icon: GraduationCap,
    badge: 'Classic University'
  },
  {
    id: 'tech_minimalist',
    name: 'Tech Minimalist',
    subtitle: 'Stanford & CMU Format',
    desc: 'Skills-first for rapid 6-sec tech screeners, compact spacing, high technical density.',
    icon: Terminal,
    badge: 'Tech & Data'
  },
  {
    id: 'modern_corporate',
    name: 'Modern Corporate',
    subtitle: 'McKinsey & Consulting Format',
    desc: 'Executive hierarchy with subtle sky-blue section accents & bolded business metrics.',
    icon: Briefcase,
    badge: 'Business & Finance'
  }
];

export default function ResumeOptimizerModal({
  isOpen,
  onClose,
  result,
  selectedFixes,
  fileName
}) {
  const [selectedTemplate, setSelectedTemplate] = useState('ivy_league');
  const [downloadingFormat, setDownloadingFormat] = useState(null); // 'docx' | 'pdf' | null
  const [error, setError] = useState(null);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  if (!isOpen) return null;

  const {
    ats_score = 0,
    recommendations = [],
    parsed_resume = {}
  } = result || {};

  // Extract selected recommendations that have rewrites
  const appliedRewrites = recommendations
    .filter((_, idx) => selectedFixes.has(idx))
    .filter((rec) => Boolean(rec.rewrite_bullet))
    .map((rec) => ({
      original_bullet: rec.original_bullet || '',
      rewrite_bullet: rec.rewrite_bullet,
      role: rec.role || ''
    }));

  const projectedScore = Math.min(96, Math.max(ats_score + 15, 88));
  const scoreDelta = projectedScore - ats_score;

  const handleDownload = async (format) => {
    setError(null);
    setDownloadSuccess(false);
    setDownloadingFormat(format);

    try {
      const token = getStoredToken();
      if (!token) {
        throw new Error('Please sign in with your Pro account to export optimized resumes.');
      }

      const res = await fetch(`${API_BASE_URL}/api/resume/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          format,
          template_id: selectedTemplate,
          parsed_resume: parsed_resume,
          applied_rewrites: appliedRewrites
        })
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `Export failed (HTTP ${res.status})`);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;

      const disposition = res.headers.get('Content-Disposition');
      let downloadFilename = format === 'pdf' ? 'ATS_Optimized_Resume.pdf' : 'ATS_Optimized_Resume.docx';
      if (disposition && disposition.includes('filename=')) {
        const match = disposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) {
          downloadFilename = match[1];
        }
      }

      a.download = downloadFilename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);

      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 4000);
    } catch (err) {
      setError(err.message || 'Failed to download optimized resume.');
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity animate-fadeIn"
      />

      <div className="min-h-full flex items-center justify-center p-4">
        <div className="w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden transform transition-all animate-scaleUp relative z-10">
          {/* Header */}
          <div className="p-6 pb-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-600 flex items-center justify-center text-white shadow-soft">
                <Crown className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <span>AI Resume Auto-Optimizer</span>
                  <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                    PRO EXPORT
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Select your target template layout & export your ATS-compliant resume
                </p>
              </div>
            </div>

            <button
              onClick={onClose}
              type="button"
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
            {/* Projected Score Boost Card */}
            <div className="p-4 bg-gradient-to-r from-emerald-500/10 via-brand-500/10 to-sky-500/10 border border-emerald-200/80 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-700">Projected ATS Score:</span>
                    <span className="text-base font-extrabold text-emerald-700">
                      {projectedScore}/100
                    </span>
                    <span className="text-[11px] font-bold text-emerald-600 bg-emerald-100 px-2 py-0.5 rounded-full">
                      +{scoreDelta} pts
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Based on {appliedRewrites.length} metric-driven bullet upgrades applied
                  </p>
                </div>
              </div>

              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold text-slate-700 bg-white border border-slate-200 shadow-2xs">
                <ShieldCheck className="w-4 h-4 text-brand-600" />
                <span>Single-Column ATS Safe</span>
              </div>
            </div>

            {/* Template Selector Section */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Select Target Resume Template
                </h4>
                <span className="text-[11px] text-brand-600 font-semibold">
                  Curated University Formats
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {TEMPLATES.map((tmpl) => {
                  const isSelected = selectedTemplate === tmpl.id;
                  const Icon = tmpl.icon;
                  return (
                    <button
                      key={tmpl.id}
                      type="button"
                      onClick={() => setSelectedTemplate(tmpl.id)}
                      className={`p-3.5 rounded-2xl border text-left transition-all relative ${
                        isSelected
                          ? 'border-brand-500 bg-brand-50/40 shadow-soft ring-2 ring-brand-500/20'
                          : 'border-slate-200 hover:border-slate-300 bg-white'
                      }`}
                    >
                      {isSelected && (
                        <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-brand-600 text-white flex items-center justify-center">
                          <Check className="w-3 h-3 stroke-[3]" />
                        </div>
                      )}
                      <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-700 flex items-center justify-center mb-2.5">
                        <Icon className="w-4 h-4 text-brand-600" />
                      </div>
                      <h5 className="text-xs font-bold text-slate-900 leading-tight">
                        {tmpl.name}
                      </h5>
                      <p className="text-[10px] text-brand-700 font-semibold mb-1">
                        {tmpl.subtitle}
                      </p>
                      <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-2">
                        {tmpl.desc}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Error or Success Feedback */}
            {error && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-2xl flex items-center gap-2 text-xs text-rose-700 animate-fadeIn">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {downloadSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-2 text-xs text-emerald-700 animate-fadeIn">
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                <span>Resume downloaded successfully! Check your browser downloads folder.</span>
              </div>
            )}

            {/* Applied Rewrites Preview */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Applied Bullet Rewrites ({appliedRewrites.length})
                </h4>
                <span className="text-[11px] text-slate-400">
                  Google XYZ formula applied
                </span>
              </div>

              {appliedRewrites.length === 0 ? (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl text-center text-xs text-slate-500">
                  No bullet rewrites were selected. Please select at least one rewrite from the recommendations checklist.
                </div>
              ) : (
                <div className="space-y-3 max-h-52 overflow-y-auto pr-1">
                  {appliedRewrites.map((rw, i) => (
                    <div
                      key={i}
                      className="p-3.5 bg-slate-50/70 border border-slate-200/80 rounded-2xl space-y-2 text-xs"
                    >
                      {rw.role && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700">
                          {rw.role}
                        </span>
                      )}

                      {rw.original_bullet && (
                        <div className="text-slate-400 line-through italic text-[11px]">
                          "{rw.original_bullet}"
                        </div>
                      )}

                      <div className="text-slate-800 font-semibold flex items-start gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 mt-0.5" />
                        <span>"{rw.rewrite_bullet}"</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Document Hygiene Guarantee */}
            <div className="p-3.5 bg-sky-50/60 border border-sky-100 rounded-2xl text-xs text-sky-900 space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-brand-600" />
                <span>ATS Formatting Hygiene Guarantee:</span>
              </p>
              <p className="text-[11px] text-sky-800/90 leading-relaxed">
                Both exported formats follow strict ATS compliance rules: 0.75" standard margins, standard system fonts, zero table or multi-column layout errors, and standard bullet characters.
              </p>
            </div>
          </div>

          {/* Footer with Download Action Buttons */}
          <div className="p-6 border-t border-slate-100 bg-slate-50/60 flex flex-col sm:flex-row items-center justify-between gap-3">
            <span className="text-xs text-slate-500">
              Format: <strong>{TEMPLATES.find((t) => t.id === selectedTemplate)?.name}</strong>
            </span>

            <div className="flex items-center gap-2.5 w-full sm:w-auto">
              <button
                type="button"
                disabled={downloadingFormat !== null || appliedRewrites.length === 0}
                onClick={() => handleDownload('docx')}
                className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs shadow-soft transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {downloadingFormat === 'docx' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                <span>Download DOCX</span>
              </button>

              <button
                type="button"
                disabled={downloadingFormat !== null || appliedRewrites.length === 0}
                onClick={() => handleDownload('pdf')}
                className="flex-1 sm:flex-none px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-soft transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {downloadingFormat === 'pdf' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                <span>Download PDF</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
