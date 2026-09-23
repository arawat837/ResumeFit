import React from 'react';
import { KeyRound, Layout, Layers, TrendingUp } from 'lucide-react';

export default function ScoreBreakdown({ breakdown, hasJd }) {
  const categories = [
    {
      key: 'keyword_match',
      title: hasJd ? 'Keyword Match' : 'General Skill Density',
      icon: KeyRound,
      score: breakdown?.keyword_match ?? 0,
      description: hasJd
        ? 'Overlap with required skills and keywords in the target job description'
        : 'Presence of standard hard skills, tools, and professional core competencies',
    },
    {
      key: 'formatting',
      title: 'Formatting Hygiene',
      icon: Layout,
      score: breakdown?.formatting ?? 0,
      description: 'Clean single-column layout free of complex tables, images, or parsing hazards',
    },
    {
      key: 'sections',
      title: 'Standard Sections',
      icon: Layers,
      score: breakdown?.sections ?? 0,
      description: 'Presence of expected ATS headings: Contact, Education, Experience, and Skills',
    },
    {
      key: 'achievements',
      title: 'Quantified Achievements',
      icon: TrendingUp,
      score: breakdown?.achievements ?? 0,
      description: 'Usage of measurable numbers (%, $, metrics) and action verbs starting bullets',
    },
  ];

  const getScoreColor = (score) => {
    if (score >= 75) return 'bg-score-high text-score-high';
    if (score >= 50) return 'bg-score-mid text-score-mid';
    return 'bg-score-low text-score-low';
  };

  return (
    <div className="w-full bg-white rounded-2xl p-6 border border-slate-200 shadow-soft">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-4">
        Category Breakdown
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {categories.map((cat) => {
          const Icon = cat.icon;
          const scoreClass = getScoreColor(cat.score);
          const barBg = scoreClass.split(' ')[0];
          const textCol = scoreClass.split(' ')[1];

          return (
            <div
              key={cat.key}
              className="p-4 rounded-xl border border-slate-100 bg-slate-50/60 hover:bg-slate-50 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center">
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="text-sm font-semibold text-slate-900">
                    {cat.title}
                  </span>
                </div>
                <span className={`text-sm font-bold ${textCol}`}>
                  {cat.score}%
                </span>
              </div>

              {/* Progress bar track */}
              <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden mb-2">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${barBg}`}
                  style={{ width: `${cat.score}%` }}
                />
              </div>

              <p className="text-xs text-slate-500 leading-normal">
                {cat.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
