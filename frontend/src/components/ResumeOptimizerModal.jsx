import React, { useState, useRef } from 'react';
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
  Check,
  UploadCloud,
  Columns2,
  ListFilter,
  FileCode,
  ArrowRight,
  RefreshCw
} from 'lucide-react';
import { getStoredToken } from '../services/auth';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const TEMPLATES = [
  {
    id: 'original',
    name: 'Keep Original Format',
    subtitle: 'Preserve Your Exact Resume Layout',
    desc: 'Maintains your original section structure, ordering, and fonts; applies surgical Google XYZ bullet improvements in-place only.',
    icon: FileText,
    badge: 'In-Place Optimization'
  },
  {
    id: 'ivy_league',
    name: 'Ivy League / Academic',
    subtitle: 'Harvard & Wharton Format',
    desc: 'Centered header, classic academic hierarchy (Education → Experience → Skills), elegant serif styling.',
    icon: GraduationCap,
    badge: 'Classic University'
  },
  {
    id: 'tech_minimalist',
    name: 'Tech Minimalist',
    subtitle: 'Stanford & CMU Format',
    desc: 'Skills-first for rapid 6-sec tech screeners, compact spacing, high technical density.',
    icon: Terminal,
    badge: 'Tech & Engineering'
  },
  {
    id: 'modern_corporate',
    name: 'Modern Corporate',
    subtitle: 'McKinsey & Consulting Format',
    desc: 'Executive hierarchy with subtle corporate accents and bolded key business impact metrics.',
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
  const [selectedTemplate, setSelectedTemplate] = useState('original');
  const [viewMode, setViewMode] = useState('split'); // 'split' | 'list'
  const [downloadingFormat, setDownloadingFormat] = useState(null); // 'docx' | 'pdf' | null
  const [error, setError] = useState(null);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  // Custom template upload state
  const [customDocxBase64, setCustomDocxBase64] = useState(null);
  const [customDocxName, setCustomDocxName] = useState(null);
  const [customUploadError, setCustomUploadError] = useState(null);
  const customFileInputRef = useRef(null);

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

  // Handle custom .docx template file upload
  const handleCustomTemplateUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.docx')) {
      setCustomUploadError('Please upload a Microsoft Word (.docx) file template.');
      return;
    }

    setCustomUploadError(null);
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const dataUrl = reader.result;
        const base64Data = dataUrl.split(',')[1];
        setCustomDocxBase64(base64Data);
        setCustomDocxName(file.name);
        setSelectedTemplate('custom');
      } catch (err) {
        setCustomUploadError('Could not process custom template file.');
      }
    };
    reader.onerror = () => {
      setCustomUploadError('Failed to read file.');
    };
    reader.readAsDataURL(file);
  };

  const handleDownload = async (format) => {
    setError(null);
    setDownloadSuccess(false);
    setDownloadingFormat(format);

    try {
      const token = getStoredToken();
      if (!token) {
        throw new Error('Please sign in with your Pro account to export optimized resumes.');
      }

      const payload = {
        format,
        template_id: selectedTemplate === 'custom' ? 'original' : selectedTemplate,
        scan_id: result?.scan_id || null,
        parsed_resume: parsed_resume,
        applied_rewrites: appliedRewrites
      };

      if (selectedTemplate === 'custom' && customDocxBase64) {
        payload.custom_template_base64 = customDocxBase64;
      }

      const res = await fetch(`${API_BASE_URL}/api/resume/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
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

  // Helper to check if a bullet has a matched rewrite
  const findRewriteForBullet = (bulletText) => {
    if (!bulletText) return null;
    const cleanB = bulletText.trim().toLowerCase();
    return appliedRewrites.find((rw) => {
      const orig = (rw.original_bullet || '').trim().toLowerCase();
      return orig && (cleanB.includes(orig) || orig.includes(cleanB));
    });
  };

  const contact = parsed_resume.contact || {};
  const candidateName = contact.name || parsed_resume.candidate_name || 'Candidate Name';
  const candidateEmail = contact.email || parsed_resume.email || '';
  const candidatePhone = contact.phone || parsed_resume.phone || '';
  const candidateLinkedin = contact.linkedin || parsed_resume.linkedin || '';
  const candidateLocation = contact.location || parsed_resume.location || '';
  const experiences = parsed_resume.experience || [];
  const education = parsed_resume.education || [];
  const skills = parsed_resume.skills || [];
  const skillsRawLines = parsed_resume.skills_raw_lines || [];
  const projects = parsed_resume.projects || [];
  const leadership = parsed_resume.leadership || [];
  const summary = parsed_resume.summary || '';

  // Determine section ordering based on template
  const isIvy = selectedTemplate === 'ivy_league';
  const isTech = selectedTemplate === 'tech_minimalist';
  const isCorporate = selectedTemplate === 'modern_corporate';
  const isCustom = selectedTemplate === 'custom';

  const templateOrderMap = {
    original: ['education', 'experience', 'projects', 'leadership', 'skills'],
    ivy_league: ['education', 'experience', 'leadership', 'projects', 'skills'],
    tech_minimalist: ['skills', 'projects', 'experience', 'education', 'leadership'],
    modern_corporate: ['experience', 'projects', 'education', 'leadership', 'skills'],
    custom: ['education', 'experience', 'projects', 'leadership', 'skills']
  };
  const activeOrder = templateOrderMap[selectedTemplate] || templateOrderMap.original;

  // Section Renderers for Side-by-Side Paper Previews
  const renderEducationSection = (isRight = false) => {
    if (!education || education.length === 0) return null;
    return (
      <div className="space-y-2">
        <h3
          className={`text-xs font-bold uppercase tracking-wider border-b pb-1 ${
            isRight
              ? isCorporate
                ? 'text-sky-800 border-sky-200'
                : 'text-slate-900 border-slate-200'
              : 'text-slate-700 border-slate-100'
          }`}
        >
          Education
        </h3>
        {education.map((edu, idx) => (
          <div key={idx} className="flex justify-between items-baseline text-[11px]">
            <div>
              <span className={`font-bold ${isRight ? 'text-slate-900' : 'text-slate-800'}`}>
                {edu.degree || 'Degree'}
              </span>
              <span className={isRight ? 'text-slate-600' : 'text-slate-500'}>
                {edu.institution ? ` — ${edu.institution}` : ''}
              </span>
            </div>
            <span className={`text-[10px] ${isRight ? 'text-slate-500 font-semibold' : 'text-slate-400'}`}>
              {edu.year || ''}
            </span>
          </div>
        ))}
      </div>
    );
  };

  const renderExperienceSection = (isRight = false) => {
    if (!experiences || experiences.length === 0) return null;
    return (
      <div className="space-y-3">
        <h3
          className={`text-xs font-bold uppercase tracking-wider border-b pb-1 ${
            isRight
              ? isCorporate
                ? 'text-sky-800 border-sky-200'
                : 'text-slate-900 border-slate-200'
              : 'text-slate-700 border-slate-100'
          }`}
        >
          {isRight ? 'Professional Experience' : 'Work Experience'}
        </h3>
        {experiences.map((exp, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex items-baseline justify-between">
              <span className={`font-bold ${isRight ? 'text-slate-900' : 'text-slate-900'}`}>
                {exp.role || 'Role'}
              </span>
              <span className={`text-[10px] ${isRight ? 'text-slate-500' : 'text-slate-400'}`}>
                {exp.duration || ''}
              </span>
            </div>
            <div className={`text-[11px] font-medium ${isRight ? 'text-slate-700' : 'text-slate-600'}`}>
              {exp.company || ''}
            </div>
            <ul
              className={`space-y-1.5 pl-4 list-disc mt-1 ${
                isRight ? 'marker:text-emerald-500' : 'marker:text-slate-400'
              }`}
            >
              {(exp.bullets || []).map((b, bIdx) => {
                const matched = findRewriteForBullet(b);
                if (isRight) {
                  return (
                    <li
                      key={bIdx}
                      className={`text-[11px] leading-relaxed transition-all ${
                        matched
                          ? 'bg-emerald-50/90 text-emerald-950 p-2 rounded-xl border border-emerald-300 shadow-2xs -ml-2 pl-2'
                          : 'text-slate-700'
                      }`}
                    >
                      {matched ? (
                        <div className="space-y-0.5">
                          <div className="flex items-center gap-1.5 text-[9px] font-extrabold text-emerald-700 uppercase tracking-wide">
                            <Sparkles className="w-3 h-3 text-emerald-600" />
                            <span>Google XYZ Formula Active</span>
                          </div>
                          <p className="font-semibold text-slate-900">
                            {matched.rewrite_bullet}
                          </p>
                        </div>
                      ) : (
                        b
                      )}
                    </li>
                  );
                } else {
                  return (
                    <li
                      key={bIdx}
                      className={`text-[11px] leading-relaxed transition-all ${
                        matched
                          ? 'bg-amber-50 text-amber-900 p-1.5 rounded-lg border border-amber-200/80 -ml-2 pl-2'
                          : 'text-slate-600'
                      }`}
                    >
                      {matched ? (
                        <div>
                          <span className="text-[9px] font-bold text-amber-700 uppercase tracking-wider block mb-0.5">
                            [Unquantified Original]
                          </span>
                          <span className="italic">{b}</span>
                        </div>
                      ) : (
                        b
                      )}
                    </li>
                  );
                }
              })}
            </ul>
          </div>
        ))}
      </div>
    );
  };

  const renderProjectsSection = (isRight = false) => {
    if (!projects || projects.length === 0) return null;
    return (
      <div className="space-y-3">
        <h3
          className={`text-xs font-bold uppercase tracking-wider border-b pb-1 ${
            isRight
              ? isCorporate
                ? 'text-sky-800 border-sky-200'
                : 'text-slate-900 border-slate-200'
              : 'text-slate-700 border-slate-100'
          }`}
        >
          Projects
        </h3>
        {projects.map((proj, idx) => {
          const title = proj.title || proj.name || 'Project';
          const org = proj.organization || proj.company || '';
          return (
            <div key={idx} className="space-y-1">
              <div className="flex items-baseline justify-between">
                <span className={`font-bold ${isRight ? 'text-slate-900' : 'text-slate-800'}`}>
                  {title}
                  {org ? ` | ${org}` : ''}
                </span>
                {proj.duration && (
                  <span className={`text-[10px] ${isRight ? 'text-slate-500' : 'text-slate-400'}`}>
                    {proj.duration}
                  </span>
                )}
              </div>
              <ul
                className={`space-y-1.5 pl-4 list-disc mt-1 ${
                  isRight ? 'marker:text-emerald-500' : 'marker:text-slate-400'
                }`}
              >
                {(proj.bullets || []).map((b, bIdx) => {
                  const matched = findRewriteForBullet(b);
                  if (isRight) {
                    return (
                      <li
                        key={bIdx}
                        className={`text-[11px] leading-relaxed transition-all ${
                          matched
                            ? 'bg-emerald-50/90 text-emerald-950 p-2 rounded-xl border border-emerald-300 shadow-2xs -ml-2 pl-2'
                            : 'text-slate-700'
                        }`}
                      >
                        {matched ? (
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1.5 text-[9px] font-extrabold text-emerald-700 uppercase tracking-wide">
                              <Sparkles className="w-3 h-3 text-emerald-600" />
                              <span>Google XYZ Formula Active</span>
                            </div>
                            <p className="font-semibold text-slate-900">
                              {matched.rewrite_bullet}
                            </p>
                          </div>
                        ) : (
                          b
                        )}
                      </li>
                    );
                  } else {
                    return (
                      <li
                        key={bIdx}
                        className={`text-[11px] leading-relaxed transition-all ${
                          matched
                            ? 'bg-amber-50 text-amber-900 p-1.5 rounded-lg border border-amber-200/80 -ml-2 pl-2'
                            : 'text-slate-600'
                        }`}
                      >
                        {matched ? (
                          <div>
                            <span className="text-[9px] font-bold text-amber-700 uppercase tracking-wider block mb-0.5">
                              [Unquantified Original]
                            </span>
                            <span className="italic">{b}</span>
                          </div>
                        ) : (
                          b
                        )}
                      </li>
                    );
                  }
                })}
              </ul>
            </div>
          );
        })}
      </div>
    );
  };

  const renderLeadershipSection = (isRight = false) => {
    if (!leadership || leadership.length === 0) return null;
    return (
      <div className="space-y-3">
        <h3
          className={`text-xs font-bold uppercase tracking-wider border-b pb-1 ${
            isRight
              ? isCorporate
                ? 'text-sky-800 border-sky-200'
                : 'text-slate-900 border-slate-200'
              : 'text-slate-700 border-slate-100'
          }`}
        >
          Leadership & Involvement
        </h3>
        {leadership.map((lead, idx) => {
          const role = lead.role || lead.title || 'Leadership';
          const org = lead.organization || lead.company || '';
          return (
            <div key={idx} className="space-y-1">
              <div className="flex items-baseline justify-between">
                <span className={`font-bold ${isRight ? 'text-slate-900' : 'text-slate-800'}`}>
                  {role}
                  {org ? ` | ${org}` : ''}
                </span>
                {lead.duration && (
                  <span className={`text-[10px] ${isRight ? 'text-slate-500' : 'text-slate-400'}`}>
                    {lead.duration}
                  </span>
                )}
              </div>
              <ul
                className={`space-y-1.5 pl-4 list-disc mt-1 ${
                  isRight ? 'marker:text-emerald-500' : 'marker:text-slate-400'
                }`}
              >
                {(lead.bullets || []).map((b, bIdx) => {
                  const matched = findRewriteForBullet(b);
                  if (isRight) {
                    return (
                      <li
                        key={bIdx}
                        className={`text-[11px] leading-relaxed transition-all ${
                          matched
                            ? 'bg-emerald-50/90 text-emerald-950 p-2 rounded-xl border border-emerald-300 shadow-2xs -ml-2 pl-2'
                            : 'text-slate-700'
                        }`}
                      >
                        {matched ? (
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-1.5 text-[9px] font-extrabold text-emerald-700 uppercase tracking-wide">
                              <Sparkles className="w-3 h-3 text-emerald-600" />
                              <span>Google XYZ Formula Active</span>
                            </div>
                            <p className="font-semibold text-slate-900">
                              {matched.rewrite_bullet}
                            </p>
                          </div>
                        ) : (
                          b
                        )}
                      </li>
                    );
                  } else {
                    return (
                      <li
                        key={bIdx}
                        className={`text-[11px] leading-relaxed transition-all ${
                          matched
                            ? 'bg-amber-50 text-amber-900 p-1.5 rounded-lg border border-amber-200/80 -ml-2 pl-2'
                            : 'text-slate-600'
                        }`}
                      >
                        {matched ? (
                          <div>
                            <span className="text-[9px] font-bold text-amber-700 uppercase tracking-wider block mb-0.5">
                              [Unquantified Original]
                            </span>
                            <span className="italic">{b}</span>
                          </div>
                        ) : (
                          b
                        )}
                      </li>
                    );
                  }
                })}
              </ul>
            </div>
          );
        })}
      </div>
    );
  };

  const renderSkillsSection = (isRight = false) => {
    if ((!skillsRawLines || skillsRawLines.length === 0) && (!skills || skills.length === 0)) return null;
    return (
      <div>
        <h3
          className={`text-xs font-bold uppercase tracking-wider border-b pb-1 mb-1.5 ${
            isRight
              ? isCorporate
                ? 'text-sky-800 border-sky-200'
                : 'text-slate-900 border-slate-200'
              : 'text-slate-700 border-slate-100'
          }`}
        >
          {isRight && isTech ? 'Technical Skills & Tooling' : 'Skills & Interests'}
        </h3>
        {skillsRawLines && skillsRawLines.length > 0 ? (
          <div className="space-y-1.5 mt-1.5">
            {skillsRawLines.map((line, idx) => {
              if (line.includes(':')) {
                const colonIdx = line.indexOf(':');
                const cat = line.substring(0, colonIdx).trim();
                const rest = line.substring(colonIdx + 1).trim();
                return (
                  <div key={idx} className="text-[11px] leading-relaxed">
                    <span className={`font-bold ${isRight ? 'text-slate-900' : 'text-slate-800'}`}>
                      {cat}:{' '}
                    </span>
                    <span className={isRight ? 'text-slate-700' : 'text-slate-600'}>
                      {rest}
                    </span>
                  </div>
                );
              }
              return (
                <div key={idx} className={`text-[11px] ${isRight ? 'text-slate-700' : 'text-slate-600'}`}>
                  {line}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {skills.map((s, idx) => (
              <span
                key={idx}
                className={`px-2 py-0.5 rounded-md text-[10px] font-medium ${
                  isRight
                    ? isTech
                      ? 'bg-slate-100 text-slate-800 font-mono'
                      : 'bg-slate-100 text-slate-800'
                    : 'bg-slate-100 text-slate-700'
                }`}
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  const renderSection = (secKey, isRight = false) => {
    switch (secKey) {
      case 'education':
        return <div key="education">{renderEducationSection(isRight)}</div>;
      case 'experience':
        return <div key="experience">{renderExperienceSection(isRight)}</div>;
      case 'projects':
        return <div key="projects">{renderProjectsSection(isRight)}</div>;
      case 'leadership':
        return <div key="leadership">{renderLeadershipSection(isRight)}</div>;
      case 'skills':
        return <div key="skills">{renderSkillsSection(isRight)}</div>;
      default:
        return null;
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity animate-fadeIn"
      />

      <div className="min-h-full flex items-center justify-center p-2 sm:p-4 md:p-6">
        <div className="w-full max-w-6xl bg-white rounded-3xl shadow-2xl border border-slate-100 overflow-hidden transform transition-all animate-scaleUp relative z-10 flex flex-col max-h-[92vh]">
          {/* Header */}
          <div className="p-4 sm:p-6 pb-4 border-b border-slate-100 flex items-center justify-between flex-shrink-0">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 to-amber-600 flex items-center justify-center text-white shadow-soft">
                <Crown className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                  <span>AI Resume Auto-Optimizer</span>
                  <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                    PRO EXPORT
                  </span>
                </h3>
                <p className="text-xs text-slate-400">
                  Compare your original resume side-by-side with your optimized Google XYZ version
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* View Switcher */}
              <div className="hidden sm:flex items-center p-1 bg-slate-100 rounded-xl text-xs font-semibold text-slate-600">
                <button
                  type="button"
                  onClick={() => setViewMode('split')}
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                    viewMode === 'split' ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'hover:text-slate-900'
                  }`}
                >
                  <Columns2 className="w-3.5 h-3.5" />
                  <span>Side-by-Side</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('list')}
                  className={`px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all ${
                    viewMode === 'list' ? 'bg-white text-slate-900 shadow-2xs font-bold' : 'hover:text-slate-900'
                  }`}
                >
                  <ListFilter className="w-3.5 h-3.5" />
                  <span>Rewrites List ({appliedRewrites.length})</span>
                </button>
              </div>

              <button
                onClick={onClose}
                type="button"
                className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Modal Scrollable Body */}
          <div className="p-4 sm:p-6 space-y-5 overflow-y-auto flex-1">
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
                    {appliedRewrites.length} Google XYZ bullet upgrades will be applied to your resume
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
                  Select Target Layout & Template
                </h4>
                <span className="text-[11px] text-brand-600 font-semibold">
                  Pick your target format or keep your original
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
                {TEMPLATES.map((tmpl) => {
                  const isSelected = selectedTemplate === tmpl.id;
                  const Icon = tmpl.icon;
                  return (
                    <button
                      key={tmpl.id}
                      type="button"
                      onClick={() => setSelectedTemplate(tmpl.id)}
                      className={`p-3 rounded-2xl border text-left transition-all relative ${
                        isSelected
                          ? 'border-brand-500 bg-brand-50/50 shadow-soft ring-2 ring-brand-500/20'
                          : 'border-slate-200 hover:border-slate-300 bg-white'
                      }`}
                    >
                      {isSelected && (
                        <div className="absolute top-2.5 right-2.5 w-4 h-4 rounded-full bg-brand-600 text-white flex items-center justify-center">
                          <Check className="w-2.5 h-2.5 stroke-[3]" />
                        </div>
                      )}
                      <div className="w-7 h-7 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center mb-2">
                        <Icon className="w-3.5 h-3.5 text-brand-600" />
                      </div>
                      <h5 className="text-xs font-bold text-slate-900 leading-tight">
                        {tmpl.name}
                      </h5>
                      <p className="text-[10px] text-brand-700 font-semibold mb-1 line-clamp-1">
                        {tmpl.subtitle}
                      </p>
                      <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2">
                        {tmpl.desc}
                      </p>
                    </button>
                  );
                })}

                {/* 5th Card: Upload Custom Template */}
                <div
                  onClick={() => customFileInputRef.current?.click()}
                  className={`p-3 rounded-2xl border text-left transition-all relative cursor-pointer ${
                    selectedTemplate === 'custom'
                      ? 'border-brand-500 bg-brand-50/50 shadow-soft ring-2 ring-brand-500/20'
                      : 'border-dashed border-slate-300 hover:border-brand-400 bg-slate-50/60'
                  }`}
                >
                  <input
                    type="file"
                    ref={customFileInputRef}
                    accept=".docx"
                    className="hidden"
                    onChange={handleCustomTemplateUpload}
                  />
                  {selectedTemplate === 'custom' && (
                    <div className="absolute top-2.5 right-2.5 w-4 h-4 rounded-full bg-brand-600 text-white flex items-center justify-center">
                      <Check className="w-2.5 h-2.5 stroke-[3]" />
                    </div>
                  )}
                  <div className="w-7 h-7 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center mb-2">
                    <UploadCloud className="w-3.5 h-3.5 text-indigo-600" />
                  </div>
                  <h5 className="text-xs font-bold text-slate-900 leading-tight flex items-center gap-1">
                    <span>Upload Template</span>
                  </h5>
                  <p className="text-[10px] text-indigo-700 font-semibold mb-1 line-clamp-1">
                    {customDocxName || 'Upload your .docx'}
                  </p>
                  <p className="text-[10px] text-slate-500 leading-relaxed line-clamp-2">
                    {customDocxName ? 'Custom template loaded.' : 'Click to select your college or personal DOCX template.'}
                  </p>
                </div>
              </div>

              {customUploadError && (
                <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 flex items-center gap-2">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{customUploadError}</span>
                </div>
              )}
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

            {/* Main Content: Side-by-Side Split View vs Rewrites List */}
            {viewMode === 'split' ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Live Before & After Resume Comparison
                  </h4>
                  <span className="text-[11px] text-slate-400">
                    Scroll to compare changes in place
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Left Column: Original Resume */}
                  <div className="bg-slate-50/80 border border-slate-200 rounded-2xl p-4 sm:p-5 flex flex-col space-y-4 max-h-[460px] overflow-y-auto shadow-inner">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-200 flex-shrink-0">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                        <span className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
                          Original Resume
                        </span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-600 font-semibold">
                        Before
                      </span>
                    </div>

                    {/* Resume Document Paper View (Original) */}
                    <div className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 space-y-4 text-xs text-slate-800 shadow-xs font-sans">
                      {/* Candidate Header */}
                      <div className="border-b border-slate-100 pb-3">
                        <h2 className="text-base font-bold text-slate-900 uppercase tracking-wide">
                          {candidateName}
                        </h2>
                        <div className="text-[11px] text-slate-500 flex flex-wrap gap-x-2 gap-y-0.5 mt-1">
                          {candidatePhone && <span>Mobile: {candidatePhone}</span>}
                          {candidateEmail && <span>{candidatePhone ? '• ' : ''}Email: {candidateEmail}</span>}
                          {candidateLinkedin && <span>• {candidateLinkedin}</span>}
                          {candidateLocation && <span>• {candidateLocation}</span>}
                        </div>
                      </div>

                      {/* Summary (if present) */}
                      {summary && (
                        <div>
                          <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                            Summary
                          </h3>
                          <p className="text-[11px] text-slate-600 leading-relaxed">{summary}</p>
                        </div>
                      )}

                      {/* All Original Sections: Education, Experience, Projects, Leadership, Skills */}
                      {['education', 'experience', 'projects', 'leadership', 'skills'].map((sec) =>
                        renderSection(sec, false)
                      )}
                    </div>
                  </div>

                  {/* Right Column: Changed and Optimised Resume */}
                  <div className="bg-emerald-50/40 border border-emerald-200/80 rounded-2xl p-4 sm:p-5 flex flex-col space-y-4 max-h-[460px] overflow-y-auto shadow-inner">
                    <div className="flex items-center justify-between pb-2 border-b border-emerald-200/80 flex-shrink-0">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="text-xs font-extrabold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5">
                          <span>Optimized Resume</span>
                          <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                        </span>
                      </div>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-extrabold border border-emerald-200">
                        {selectedTemplate === 'original'
                          ? 'In-Place Rewrites'
                          : selectedTemplate === 'custom'
                          ? 'Custom Template'
                          : TEMPLATES.find((t) => t.id === selectedTemplate)?.name}
                      </span>
                    </div>

                    {/* Resume Document Paper View (Optimized with Google XYZ) */}
                    <div
                      className={`bg-white border border-emerald-200 rounded-xl p-4 sm:p-5 space-y-4 text-xs text-slate-800 shadow-xs ${
                        isIvy ? 'font-serif' : 'font-sans'
                      }`}
                    >
                      {/* Candidate Header (Centered for Ivy League, Left for others) */}
                      <div
                        className={`border-b pb-3 ${
                          isIvy ? 'text-center border-slate-200' : 'text-left border-slate-100'
                        }`}
                      >
                        <h2
                          className={`text-base font-extrabold uppercase tracking-wide ${
                            isCorporate ? 'text-sky-900' : 'text-slate-900'
                          }`}
                        >
                          {candidateName}
                        </h2>
                        <div
                          className={`text-[11px] text-slate-500 flex flex-wrap gap-x-2 gap-y-0.5 mt-1 ${
                            isIvy ? 'justify-center' : 'justify-start'
                          }`}
                        >
                          {candidatePhone && <span>Mobile: {candidatePhone}</span>}
                          {candidateEmail && <span>{candidatePhone ? '• ' : ''}Email: {candidateEmail}</span>}
                          {candidateLinkedin && <span>• {candidateLinkedin}</span>}
                          {candidateLocation && <span>• {candidateLocation}</span>}
                        </div>
                      </div>

                      {/* Summary (if present and corporate) */}
                      {summary && isCorporate && (
                        <div>
                          <h3 className="text-xs font-bold text-sky-800 uppercase tracking-wider mb-1">
                            Summary
                          </h3>
                          <p className="text-[11px] text-slate-600 leading-relaxed">{summary}</p>
                        </div>
                      )}

                      {/* All Template Sections in Ordered Sequence */}
                      {activeOrder.map((sec) => renderSection(sec, true))}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* ViewMode: Detailed Rewrites List */
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Applied Bullet Rewrites ({appliedRewrites.length})
                  </h4>
                  <span className="text-[11px] text-slate-400">
                    Google XYZ formula: Accomplished [X], measured by [Y], by doing [Z]
                  </span>
                </div>

                {appliedRewrites.length === 0 ? (
                  <div className="p-6 bg-slate-50 border border-slate-200 rounded-2xl text-center text-xs text-slate-500">
                    No bullet rewrites selected. Check the recommendation checkboxes in the results screen.
                  </div>
                ) : (
                  <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                    {appliedRewrites.map((rw, i) => (
                      <div
                        key={i}
                        className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-2 text-xs"
                      >
                        {rw.role && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white border border-slate-200 text-slate-700">
                            {rw.role}
                          </span>
                        )}

                        {rw.original_bullet && (
                          <div className="p-2.5 bg-rose-50/60 border border-rose-100 rounded-xl text-rose-950 text-[11px] line-through italic">
                            "{rw.original_bullet}"
                          </div>
                        )}

                        <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-950 font-semibold flex items-start gap-2">
                          <Sparkles className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <span>"{rw.rewrite_bullet}"</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

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
          <div className="p-4 sm:p-6 border-t border-slate-100 bg-slate-50/80 flex flex-col sm:flex-row items-center justify-between gap-3 flex-shrink-0">
            <div className="text-xs text-slate-600 flex items-center gap-2">
              <span>Target:</span>
              <strong className="text-slate-900">
                {selectedTemplate === 'custom'
                  ? `Custom Template (${customDocxName || 'User Template'})`
                  : TEMPLATES.find((t) => t.id === selectedTemplate)?.name}
              </strong>
              <span className="text-[11px] text-slate-400">
                ({appliedRewrites.length} rewrites applied)
              </span>
            </div>

            <div className="flex items-center gap-2.5 w-full sm:w-auto">
              <button
                type="button"
                disabled={downloadingFormat !== null || appliedRewrites.length === 0}
                onClick={() => handleDownload('docx')}
                className="flex-1 sm:flex-none px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-700 text-white font-bold text-xs shadow-soft transition-all disabled:opacity-50 flex items-center justify-center gap-2 transform hover:scale-[1.01]"
              >
                {downloadingFormat === 'docx' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                <span>Download Word (.docx)</span>
              </button>

              <button
                type="button"
                disabled={downloadingFormat !== null || appliedRewrites.length === 0}
                onClick={() => handleDownload('pdf')}
                className="flex-1 sm:flex-none px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs shadow-soft transition-all disabled:opacity-50 flex items-center justify-center gap-2 transform hover:scale-[1.01]"
              >
                {downloadingFormat === 'pdf' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                <span>Download PDF (.pdf)</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
