import React, { useState } from 'react';
import { X, Sparkles, Crown, Download, RefreshCw, LayoutTemplate, CheckCircle2, AlertCircle, Loader2, ArrowRight, KeyRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function UpgradeModal({ isOpen, onClose, onOpenAuth }) {
  const { user, isLoggedIn, isPro, redeem } = useAuth();
  const [promoCode, setPromoCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  if (!isOpen) return null;

  const proFeatures = [
    {
      title: 'Full 5–7 Actionable Recommendations',
      desc: 'Unlocks all diagnostic bullet rewrites following the proven Google XYZ formula.',
      icon: Sparkles,
    },
    {
      title: '1-Click "Generate Updated Resume"',
      desc: 'Automatically apply suggested edits and download a cleanly formatted, ATS-compliant DOCX or PDF.',
      icon: Download,
    },
    {
      title: 'Reference & University Template Matching',
      desc: "Restructure your resume layout to match Ivy League and standard university formats.",
      icon: LayoutTemplate,
    },
    {
      title: 'Unlimited Scans & Re-scans',
      desc: 'Scan unlimited resume iterations with persistent account history across devices.',
      icon: RefreshCw,
    },
  ];

  const handleRedeem = async (e) => {
    e.preventDefault();
    if (!promoCode.trim()) return;

    setError(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const res = await redeem(promoCode.trim());
      setSuccessMsg(res.message || 'ResumeFit Pro activated successfully!');
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to redeem promo code.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-8 border border-slate-200 shadow-2xl relative animate-scaleUp">
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          aria-label="Close upgrade modal"
          className="absolute top-5 right-5 p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          {isPro ? (
            <span className="px-2.5 py-1 rounded-full text-xs font-extrabold bg-gradient-to-r from-amber-500 to-amber-600 text-white flex items-center gap-1 shadow-xs">
              <Crown className="w-3.5 h-3.5" />
              <span>ResumeFit Pro Active</span>
            </span>
          ) : (
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-brand-100 text-brand-700 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Phase 3 Pro Tier</span>
            </span>
          )}
        </div>

        <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight mb-2">
          {isPro ? 'You Have Active Pro Access!' : (
            <>Unlock ResumeFit <span className="text-brand-600">Pro</span></>
          )}
        </h3>

        <p className="text-xs sm:text-sm text-slate-500 mb-5">
          {isPro
            ? `Your account (${user?.email}) has permanent ResumeFit Pro access. All 7 recommendations and export features are unlocked.`
            : 'Everything you need to turn rejection emails into interview invitations. Built for university & MBA students.'}
        </p>

        {/* Feature Cards */}
        <div className="space-y-2.5 mb-5">
          {proFeatures.map((feat, idx) => {
            const Icon = feat.icon;
            return (
              <div
                key={idx}
                className="p-3 rounded-2xl border border-brand-100 bg-brand-50/40 flex items-start gap-3"
              >
                <div className="w-7 h-7 rounded-lg bg-brand-600 text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-xs">
                  <Icon className="w-3.5 h-3.5" />
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

        {/* Action Section */}
        {isPro ? (
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            <div className="text-xs text-emerald-800">
              <p className="font-bold">Permanent Pro Account Active</p>
              <p className="text-[11px] text-emerald-700">
                Code applied: <span className="font-mono font-semibold">{user?.pro_code_used || 'PRO'}</span>. No further action needed.
              </p>
            </div>
          </div>
        ) : !isLoggedIn ? (
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
            <div className="flex items-start gap-2.5 text-xs text-slate-700">
              <KeyRound className="w-4 h-4 text-brand-600 flex-shrink-0 mt-0.5" />
              <p>
                <strong>Have a team or campus promo code?</strong> Please sign in or create an account first so your Pro upgrade is saved permanently to your profile.
              </p>
            </div>
            <button
              type="button"
              onClick={() => {
                onClose();
                if (onOpenAuth) onOpenAuth();
              }}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 flex items-center justify-center gap-2 transition-all shadow-xs"
            >
              <span>Sign In / Create Free Account</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ) : (
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                <KeyRound className="w-3.5 h-3.5 text-brand-600" />
                <span>Redeem Team / Campus Code</span>
              </span>
              <span className="text-[10px] text-slate-400">
                Signed in as: <strong>{user?.name}</strong>
              </span>
            </div>

            {error && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-2 text-xs text-rose-700 animate-fadeIn">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}
            {successMsg && (
              <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-xs text-emerald-700 animate-fadeIn">
                <CheckCircle2 className="w-3.5 h-3.5 flex-shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            <form onSubmit={handleRedeem} className="flex gap-2">
              <input
                type="text"
                required
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                placeholder="e.g. CAMPUS2026 or TEACHERVIP"
                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-xs uppercase font-mono font-semibold placeholder:font-sans placeholder:normal-case placeholder:font-normal focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <button
                type="submit"
                disabled={loading || !promoCode.trim()}
                className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-brand-600 hover:bg-brand-700 disabled:opacity-50 transition-all flex items-center gap-1.5 shadow-xs"
              >
                {loading ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <span>Activate</span>
                )}
              </button>
            </form>

            <p className="text-[11px] text-slate-400 leading-tight">
              Tip: Team members & instructors can use code <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-700">CAMPUS2026</code> or <code className="bg-slate-200 px-1 py-0.5 rounded text-slate-700">TEACHERVIP</code>.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
