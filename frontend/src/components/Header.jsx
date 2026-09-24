import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, FileCheck2, Clock, LogIn, LogOut, Crown, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Header({ onOpenUpgrade, onOpenHistory, onOpenAuth, historyCount = 0 }) {
  const { user, isLoggedIn, isPro, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getInitials = (name) => {
    if (!name) return 'U';
    const parts = name.trim().split(/\s+/);
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <header className="w-full bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-40 transition-all">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Logo & Tagline */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-brand-400 flex items-center justify-center text-white shadow-soft">
            <FileCheck2 className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-slate-900">
                Resume<span className="text-brand-600">Fit</span>
              </span>
              {isPro ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-extrabold px-2.5 py-0.5 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-xs">
                  <Crown className="w-3 h-3" />
                  <span>PRO</span>
                </span>
              ) : (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-100 text-brand-700">
                  Student Beta
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Calm, explainable ATS scores & actionable recommendations
            </p>
          </div>
        </div>

        {/* Action Triggers: History, Upgrade & Auth */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* History Button */}
          <button
            type="button"
            onClick={onOpenHistory}
            aria-label="Open scan history"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 transition-colors shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span className="hidden sm:inline">History</span>
            {historyCount > 0 && (
              <span className="ml-0.5 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-brand-100 text-brand-700">
                {historyCount}
              </span>
            )}
          </button>

          {/* Pro Status / Upgrade Trigger */}
          {isPro ? (
            <button
              type="button"
              onClick={onOpenUpgrade}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold text-amber-800 bg-amber-50 hover:bg-amber-100 border border-amber-200 transition-colors shadow-xs"
            >
              <Crown className="w-3.5 h-3.5 text-amber-600" />
              <span>ResumeFit Pro</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={onOpenUpgrade}
              aria-label="Open ResumeFit Pro information"
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold text-brand-700 bg-brand-50 hover:bg-brand-100 border border-brand-200 transition-colors shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
            >
              <Sparkles className="w-3.5 h-3.5 text-brand-500" />
              <span>ResumeFit Pro</span>
            </button>
          )}

          {/* Authentication State */}
          {isLoggedIn ? (
            <div className="relative" ref={dropdownRef}>
              <button
                type="button"
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-1.5 pl-2 pr-2.5 py-1 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-100 border border-slate-200 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs ${
                  isPro ? 'bg-gradient-to-tr from-amber-500 to-amber-600 text-white' : 'bg-brand-100 text-brand-700'
                }`}>
                  {getInitials(user?.name)}
                </div>
                <span className="hidden md:inline max-w-[100px] truncate text-slate-800">
                  {user?.name || 'Account'}
                </span>
                <ChevronDown className="w-3 h-3 text-slate-400" />
              </button>

              {/* Profile Dropdown */}
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 z-50 animate-scaleUp">
                  <div className="px-4 py-2.5 border-b border-slate-100">
                    <p className="text-xs font-bold text-slate-900 truncate">
                      {user?.name}
                    </p>
                    <p className="text-[11px] text-slate-400 truncate">
                      {user?.email}
                    </p>
                    <div className="mt-2">
                      {isPro ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
                          <Crown className="w-2.5 h-2.5" />
                          <span>ResumeFit Pro Active</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-600">
                          <span>Free Plan</span>
                        </span>
                      )}
                    </div>
                  </div>

                  {!isPro && (
                    <button
                      type="button"
                      onClick={() => {
                        setDropdownOpen(false);
                        onOpenUpgrade();
                      }}
                      className="w-full text-left px-4 py-2 text-xs font-semibold text-brand-600 hover:bg-brand-50 flex items-center gap-2"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Redeem Pro Code</span>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => {
                      logout();
                      setDropdownOpen(false);
                    }}
                    className="w-full text-left px-4 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50 flex items-center gap-2"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Sign Out</span>
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              type="button"
              onClick={onOpenAuth}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 transition-colors shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
