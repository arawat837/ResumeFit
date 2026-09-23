import React from 'react';
import { Target, Briefcase, FileCode } from 'lucide-react';

export default function ModeSelector({
  mode,
  onModeChange,
  presets,
  selectedRoleId,
  onRoleChange,
  customJd,
  onCustomJdChange
}) {
  const options = [
    {
      id: 'general',
      title: 'General ATS Score',
      desc: 'Check resume against industry ATS standards, core skills, formatting, and metrics.',
      icon: Target
    },
    {
      id: 'preset',
      title: 'Target Popular Role',
      desc: 'Select from preset university roles: Data Analyst, Consultant, Marketing, or HR.',
      icon: Briefcase
    },
    {
      id: 'custom',
      title: 'Paste Job Description',
      desc: 'Paste the exact job posting to see keyword match percentage and tailored fixes.',
      icon: FileCode
    }
  ];

  const currentPreset = presets?.find((p) => p.id === selectedRoleId) || presets?.[0];

  return (
    <div className="w-full bg-white rounded-2xl p-6 border border-slate-200 shadow-soft">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">
        Step 2: Choose Scoring Mode
      </h3>

      {/* Mode Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {options.map((opt) => {
          const Icon = opt.icon;
          const isSelected = mode === opt.id;
          return (
            <button
              key={opt.id}
              type="button"
              onClick={() => onModeChange(opt.id)}
              className={`text-left p-4 rounded-xl border transition-all duration-200 flex flex-col justify-between ${
                isSelected
                  ? 'border-brand-500 bg-brand-50/70 shadow-sm ring-1 ring-brand-400'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/60'
              }`}
            >
              <div>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-3 ${
                  isSelected ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-600'
                }`}>
                  <Icon className="w-4 h-4" />
                </div>
                <h4 className={`text-sm font-semibold mb-1 ${
                  isSelected ? 'text-brand-900' : 'text-slate-800'
                }`}>
                  {opt.title}
                </h4>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {opt.desc}
                </p>
              </div>
            </button>
          );
        })}
      </div>

      {/* Sub-panels for Mode Details */}
      {mode === 'preset' && (
        <div className="mt-5 p-4 rounded-xl bg-slate-50 border border-slate-200">
          <label className="block text-xs font-semibold text-slate-700 mb-2">
            Select Target Role
          </label>
          <select
            value={selectedRoleId}
            onChange={(e) => onRoleChange(e.target.value)}
            className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-brand-500 transition-shadow"
          >
            {presets?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>

          {currentPreset && (
            <div className="mt-3 pt-3 border-t border-slate-200/80">
              <p className="text-xs text-slate-600 mb-2 font-medium">
                Key Skills Targeted:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {currentPreset.required_skills?.map((skill, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-brand-100/70 text-brand-800"
                  >
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {mode === 'custom' && (
        <div className="mt-5">
          <div className="flex justify-between items-center mb-1.5">
            <label className="block text-xs font-semibold text-slate-700">
              Paste Target Job Description
            </label>
            <span className="text-xs text-slate-400">
              {customJd.trim() ? `${customJd.trim().split(/\s+/).length} words` : '0 words'}
            </span>
          </div>
          <textarea
            rows={4}
            value={customJd}
            onChange={(e) => onCustomJdChange(e.target.value)}
            placeholder="Paste the job description or internship requirements here..."
            className="w-full bg-slate-50 border border-slate-300 rounded-xl p-3.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:border-brand-500 focus:bg-white transition-all resize-y"
          />
        </div>
      )}
    </div>
  );
}
