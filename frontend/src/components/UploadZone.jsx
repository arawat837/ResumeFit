import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, X } from 'lucide-react';

const MAX_SIZE_BYTES = 5 * 1024 * 1024; // 5MB

export default function UploadZone({ selectedFile, onFileSelect, onFileRemove, errorMessage }) {
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState(null);
  const fileInputRef = useRef(null);

  const validateAndSetFile = (file) => {
    setLocalError(null);
    if (!file) return;

    // Check size limit: 5MB
    if (file.size > MAX_SIZE_BYTES) {
      setLocalError(`File size (${(file.size / (1024 * 1024)).toFixed(2)} MB) exceeds the 5MB maximum limit. Please upload a smaller file.`);
      return;
    }

    // Check file extension
    const name = file.name.toLowerCase();
    if (!name.endsWith('.pdf') && !name.endsWith('.docx')) {
      setLocalError('Only PDF (.pdf) and Word documents (.docx) are supported.');
      return;
    }

    onFileSelect(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const activeError = localError || errorMessage;

  return (
    <div className="w-full">
      {/* Upload Box */}
      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative border-2 border-dashed rounded-2xl p-8 sm:p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 bg-white/70 hover:bg-white hover:border-brand-400 ${
            isDragging
              ? 'border-brand-500 bg-brand-50/80 scale-[1.01]'
              : 'border-slate-200 shadow-soft'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={handleInputChange}
            className="hidden"
          />

          <div className="w-16 h-16 rounded-2xl bg-brand-50 text-brand-600 flex items-center justify-center mb-4 transition-transform group-hover:scale-105 border border-brand-100">
            <UploadCloud className="w-8 h-8 stroke-[1.75]" />
          </div>

          <h3 className="text-base font-semibold text-slate-900 mb-1">
            Drag and drop your resume here
          </h3>
          <p className="text-sm text-slate-500 mb-3 max-w-sm">
            Upload your resume in <span className="font-medium text-slate-700">PDF</span> or <span className="font-medium text-slate-700">DOCX</span> format (max 5MB)
          </p>

          <span className="inline-flex items-center px-4 py-2 rounded-xl text-xs font-semibold text-brand-700 bg-brand-100 hover:bg-brand-200 transition-colors">
            Browse from device
          </span>
        </div>
      ) : (
        /* Selected File Card */
        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-soft flex items-center justify-between transition-all">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-brand-50 text-brand-600 flex items-center justify-center border border-brand-100 flex-shrink-0">
              <FileText className="w-6 h-6 stroke-[1.75]" />
            </div>
            <div className="overflow-hidden">
              <div className="flex items-center gap-2">
                <p className="text-sm font-semibold text-slate-900 truncate max-w-xs sm:max-w-md">
                  {selectedFile.name}
                </p>
                <CheckCircle2 className="w-4 h-4 text-score-high flex-shrink-0" />
              </div>
              <p className="text-xs text-slate-500">
                {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Ready to scan
              </p>
            </div>
          </div>

          <button
            onClick={onFileRemove}
            className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
            title="Remove file"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Error Banner */}
      {activeError && (
        <div className="mt-4 p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-sm text-red-700 animate-fadeIn">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500" />
          <div className="flex-1">
            <p className="font-medium text-red-900">Upload Issue</p>
            <p className="text-xs mt-0.5 leading-relaxed text-red-700">{activeError}</p>
          </div>
        </div>
      )}
    </div>
  );
}
