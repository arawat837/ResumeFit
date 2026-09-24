import React, { useEffect, useRef } from 'react';
import { X, Clock, Trash2, FileText, ArrowRight, Sparkles, Scale } from 'lucide-react';
import { formatRelativeTime } from '../services/history';

export default function HistoryDrawer({
  isOpen,
  onClose,
  history,
  onSelectScan,
  onClearHistory
}) {
  const drawerRef = useRef(null);
  const closeButtonRef = useRef(null);
  const triggerRef = useRef(null);

  // Focus management: capture trigger, auto-focus close button on open, restore focus on close
  useEffect(() => {
    if (isOpen) {
      triggerRef.current = document.activeElement;
      // Focus close button on next frame after mounting
      const frameId = requestAnimationFrame(() => {
        closeButtonRef.current?.focus();
      });
      return () => cancelAnimationFrame(frameId);
    } else if (triggerRef.current && typeof triggerRef.current.focus === 'function') {
      triggerRef.current.focus();
      triggerRef.current = null;
    }
  }, [isOpen]);

  // Keyboard navigation: Escape to close and Tab-trapping within drawer
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        const focusableElements = drawerRef.current?.querySelectorAll(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (!focusableElements || focusableElements.length === 0) return;

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getScoreBadge = (score) => {
    if (score >= 75) {
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
    if (score >= 50) {
      return 'bg-amber-50 text-amber-700 border-amber-200';
    }
    return 'bg-rose-50 text-rose-700 border-rose-200';
  };

  const formatModeLabel = (mode, roleId) => {
    if (mode === 'preset') {
      const formatted = roleId ? roleId.replace(/_/g, ' ') : 'Preset';
      return formatted.charAt(0).toUpperCase() + formatted.slice(1);
    }
    if (mode === 'custom') return 'Custom JD';
    return 'General ATS';
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" role="dialog" aria-modal="true" aria-labelledby="history-drawer-title">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs transition-opacity animate-fadeIn"
      />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div
          ref={drawerRef}
          className="w-screen max-w-md bg-white border-l border-slate-200 shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out animate-slideLeft"
        >
          {/* Drawer Header */}
          <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-brand-50 text-brand-600 flex items-center justify-center border border-brand-100">
                <Clock className="w-4 h-4" />
              </div>
              <div>
                <h3 id="history-drawer-title" className="text-base font-bold text-slate-900">
                  Scan History
                </h3>
                <p className="text-xs text-slate-400">
                  This Session • Max 10 Scans
                </p>
              </div>
            </div>

            <button
              ref={closeButtonRef}
              onClick={onClose}
              type="button"
              aria-label="Close scan history"
              className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
            {history.length === 0 ? (
              <div className="py-16 text-center space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
                  <FileText className="w-6 h-6" />
                </div>
                <h4 className="text-sm font-semibold text-slate-700">
                  No scans yet in this session
                </h4>
                <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
                  Upload a resume on the main screen to evaluate its ATS compatibility. Your recent scans will appear here for instant review.
                </p>
              </div>
            ) : (
              history.map((scan) => {
                const scoreBadge = getScoreBadge(scan.ats_score);
                const isGemini = scan.engine === 'gemini';

                return (
                  <button
                    key={scan.id}
                    type="button"
                    onClick={() => {
                      onSelectScan(scan);
                      onClose();
                    }}
                    className="w-full text-left p-4 rounded-xl border border-slate-200 hover:border-brand-400 bg-white hover:bg-brand-50/40 shadow-xs hover:shadow-soft transition-all group flex items-start justify-between gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-semibold text-slate-900 truncate">
                          {scan.filename}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 text-[11px] text-slate-400 mb-2">
                        <span>{formatRelativeTime(scan.timestamp)}</span>
                        <span>•</span>
                        <span className="capitalize">{formatModeLabel(scan.mode, scan.roleId)}</span>
                      </div>

                      <div className="flex items-center gap-1.5">
                        {isGemini ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-brand-100 text-brand-700">
                            <Sparkles className="w-2.5 h-2.5" />
                            <span>Gemini</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600">
                            <Scale className="w-2.5 h-2.5" />
                            <span>Rubric</span>
                          </span>
                        )}
                        <span className="text-[11px] text-slate-400">
                          {scan.recommendations?.length || 0} fixes
                        </span>
                      </div>
                    </div>

                    {/* Score Badge */}
                    <div className="flex flex-col items-end gap-2 flex-shrink-0">
                      <span className={`px-2.5 py-1 rounded-lg text-xs font-extrabold border ${scoreBadge}`}>
                        {scan.ats_score}
                      </span>
                      <span className="text-[11px] font-semibold text-brand-600 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                        <span>View</span>
                        <ArrowRight className="w-3 h-3" />
                      </span>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Drawer Footer */}
          {history.length > 0 && (
            <div className="p-4 border-t border-slate-100 bg-slate-50/60 flex items-center justify-between text-xs text-slate-500">
              <span className="text-[11px] text-slate-400">
                Session data (clears on tab close)
              </span>

              <button
                type="button"
                onClick={onClearHistory}
                aria-label="Clear all scan history"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-red-600 hover:text-red-700 hover:bg-red-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear history</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
