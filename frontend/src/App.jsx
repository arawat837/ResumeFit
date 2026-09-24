import React, { useState, useEffect } from 'react';
import { ArrowRight, Sparkles, ShieldCheck } from 'lucide-react';
import Header from './components/Header';
import UploadZone from './components/UploadZone';
import ModeSelector from './components/ModeSelector';
import ProcessingScreen from './components/ProcessingScreen';
import ResultsScreen from './components/ResultsScreen';
import UpgradeModal from './components/UpgradeModal';
import HistoryDrawer from './components/HistoryDrawer';
import AuthModal from './components/AuthModal';
import { fetchPresets, scanResume } from './services/api';
import { getScanHistory, saveScanResult, clearScanHistory } from './services/history';

export default function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [mode, setMode] = useState('general');
  const [selectedRoleId, setSelectedRoleId] = useState('data_analyst');
  const [customJd, setCustomJd] = useState('');
  const [presets, setPresets] = useState([]);

  // Scanning flow states: 'idle' | 'processing' | 'results'
  const [status, setStatus] = useState('idle');
  const [isApiComplete, setIsApiComplete] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isUpgradeModalOpen, setIsUpgradeModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Session-based scan history state
  const [history, setHistory] = useState([]);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  // Load preset job descriptions and session history on mount
  useEffect(() => {
    fetchPresets().then((data) => {
      setPresets(data);
      if (data && data.length > 0) {
        setSelectedRoleId(data[0].id);
      }
    });

    // Safe session storage read
    setHistory(getScanHistory());
  }, []);

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setErrorMessage(null);
  };

  const handleFileRemove = () => {
    setSelectedFile(null);
    setErrorMessage(null);
  };

  const handleStartScan = async () => {
    if (!selectedFile) return;

    setStatus('processing');
    setIsApiComplete(false);
    setErrorMessage(null);

    try {
      const result = await scanResume({
        file: selectedFile,
        mode,
        roleId: selectedRoleId,
        customJd,
      });

      setScanResult(result);
      // Mark API complete so the ProcessingScreen can wrap up its animated steps
      setIsApiComplete(true);

      // Save to browser sessionStorage under resumefit_scan_history (max 10 items)
      const updatedHistory = saveScanResult({
        filename: selectedFile.name,
        mode,
        roleId: selectedRoleId,
        result,
      });
      setHistory(updatedHistory);
    } catch (err) {
      console.error('Scan error:', err);
      setErrorMessage(err.message || 'Failed to scan resume. Please try again.');
      setStatus('idle');
      setIsApiComplete(false);
    }
  };

  const handleProcessingAnimationFinished = () => {
    setStatus('results');
  };

  const handleResetScan = () => {
    setStatus('idle');
    setScanResult(null);
    setIsApiComplete(false);
    setErrorMessage(null);
  };

  // Re-render ResultsScreen directly from cached session history (NO new API call)
  const handleSelectHistoryScan = (cachedScan) => {
    setScanResult(cachedScan);
    setSelectedFile({ name: cachedScan.filename });
    setStatus('results');
    setErrorMessage(null);
  };

  const handleClearHistory = () => {
    clearScanHistory();
    setHistory([]);
  };

  return (
    <div className="min-h-screen bg-brand-50 text-slate-900 flex flex-col font-sans selection:bg-brand-200 overflow-x-hidden">
      {/* Navigation Header */}
      <Header
        onOpenUpgrade={() => setIsUpgradeModalOpen(true)}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        historyCount={history.length}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* VIEW 1: UPLOAD & MODE SELECTION */}
        {status === 'idle' && (
          <div className="space-y-8 animate-fadeIn">
            {/* Hero / Intro */}
            <div className="text-center max-w-2xl mx-auto space-y-3">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-semibold bg-white border border-brand-200 text-brand-700 shadow-soft">
                <Sparkles className="w-3.5 h-3.5 text-brand-500" />
                <span>Applicant Tracking System (ATS) Diagnostic</span>
              </div>
              <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight leading-tight">
                Get Past the ATS Robots. <br className="hidden sm:inline" />
                <span className="text-brand-600">Land the Interview.</span>
              </h1>
              <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-xl mx-auto">
                Upload your resume for an instant, explainable compatibility score with AI-powered, actionable bullet suggestions tailored for students.
              </p>
            </div>

            {/* Step 1: Upload Zone */}
            <div className="space-y-2">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 px-1">
                Step 1: Upload Your Resume
              </h3>
              <UploadZone
                selectedFile={selectedFile}
                onFileSelect={handleFileSelect}
                onFileRemove={handleFileRemove}
                errorMessage={errorMessage}
                onClearError={() => setErrorMessage(null)}
              />
            </div>

            {/* Step 2: Mode Selector */}
            <ModeSelector
              mode={mode}
              onModeChange={setMode}
              presets={presets}
              selectedRoleId={selectedRoleId}
              onRoleChange={setSelectedRoleId}
              customJd={customJd}
              onCustomJdChange={setCustomJd}
            />

            {/* Scan Action Button */}
            <div className="pt-2 text-center">
              <button
                type="button"
                onClick={handleStartScan}
                disabled={!selectedFile}
                className={`inline-flex items-center justify-center gap-2.5 px-8 py-4 rounded-2xl text-sm font-bold shadow-soft transition-all transform ${
                  selectedFile
                    ? 'bg-brand-600 hover:bg-brand-700 text-white cursor-pointer hover:scale-[1.02] shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }`}
              >
                <span>Calculate ATS Compatibility Score</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <div className="flex items-center justify-center gap-4 text-[11px] text-slate-400 mt-4">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                  In-memory processing (no accounts or storage)
                </span>
                <span>•</span>
                <span>PDF & DOCX supported</span>
              </div>
            </div>
          </div>
        )}

        {/* VIEW 2: LIVE MULTI-STEP PROCESSING */}
        {status === 'processing' && (
          <div className="py-12 animate-fadeIn">
            <ProcessingScreen
              mode={mode}
              isComplete={isApiComplete}
              onFinishAnimation={handleProcessingAnimationFinished}
            />
          </div>
        )}

        {/* VIEW 3: RESULTS SCREEN */}
        {status === 'results' && scanResult && (
          <div className="animate-fadeIn">
            <ResultsScreen
              result={scanResult}
              fileName={selectedFile?.name}
              onReset={handleResetScan}
              onOpenUpgrade={() => setIsUpgradeModalOpen(true)}
            />
          </div>
        )}
      </main>

      {/* Session Scan History Drawer */}
      <HistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        history={history}
        onSelectScan={handleSelectHistoryScan}
        onClearHistory={handleClearHistory}
      />

      {/* Pro Upgrade Roadmap Modal */}
      <UpgradeModal
        isOpen={isUpgradeModalOpen}
        onClose={() => setIsUpgradeModalOpen(false)}
        onOpenAuth={() => setIsAuthModalOpen(true)}
      />

      {/* User Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={() => setIsUpgradeModalOpen(true)}
      />

      {/* Simple Footer */}
      <footer className="w-full border-t border-slate-200/80 bg-white/60 py-6 text-center text-xs text-slate-400">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>ResumeFit • Built for student job seekers</span>
          <span>Calm design system • 100% explainable rubric scoring</span>
        </div>
      </footer>
    </div>
  );
}
