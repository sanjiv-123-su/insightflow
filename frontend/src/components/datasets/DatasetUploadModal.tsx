import React, { useState, useRef } from 'react';
import { datasetService } from '../../services/datasetService';
import { getErrorMessage } from '../../services/api';
import type { DatasetUploadResponse } from '../../types';

import {
  UploadCloud,
  FileSpreadsheet,
  FileText,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';

interface DatasetUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (dataset: DatasetUploadResponse) => void;
}

export const DatasetUploadModal: React.FC<DatasetUploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSelectFile = (selected: File) => {
    setError(null);
    const validExts = ['.csv', '.xlsx'];
    const hasValidExt = validExts.some((ext) => selected.name.toLowerCase().endsWith(ext));

    if (!hasValidExt) {
      setError('Please select a valid CSV or XLSX file');
      return;
    }

    if (selected.size > 50 * 1024 * 1024) {
      setError('File size exceeds the 50MB maximum limit');
      return;
    }

    setFile(selected);
    if (!name) {
      // Pre-fill clean name from file
      const baseName = selected.name.replace(/\.[^/.]+$/, '');
      setName(baseName.replace(/[_-]/g, ' '));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSelectFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to upload');
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      const result = await datasetService.uploadDataset(file, name.trim() || undefined);
      onSuccess(result);
      onClose();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-lg rounded-2xl p-6 shadow-2xl relative border border-slate-700/60">
        <button
          onClick={onClose}
          disabled={isUploading}
          className="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-brand-500/15 border border-brand-500/25 flex items-center justify-center text-brand-400">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Upload New Dataset</h3>
            <p className="text-xs text-slate-400">Supported formats: CSV or XLSX up to 50MB</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-200 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Dropzone */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
              dragActive
                ? 'border-brand-500 bg-brand-500/10'
                : file
                ? 'border-emerald-500/40 bg-emerald-500/5'
                : 'border-slate-700 hover:border-slate-500 bg-slate-900/40 hover:bg-slate-900/70'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              onChange={handleFileInput}
              className="hidden"
            />

            {file ? (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center mb-2">
                  {file.name.endsWith('.csv') ? (
                    <FileText className="w-6 h-6" />
                  ) : (
                    <FileSpreadsheet className="w-6 h-6" />
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-200 truncate max-w-xs">{file.name}</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; Ready to upload
                </p>
                <span className="text-[11px] text-brand-400 mt-2 hover:underline">
                  Click or drop to replace
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-slate-800/80 text-slate-400 flex items-center justify-center mb-2">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <p className="text-sm font-medium text-slate-300">
                  Drag and drop your file here, or{' '}
                  <span className="text-brand-400 font-semibold">browse</span>
                </p>
                <p className="text-xs text-slate-400 mt-1">Accepts .csv and .xlsx files</p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
              Dataset Name (Optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q3 Sales & Orders"
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 placeholder:text-slate-400"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || isUploading}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-xs transition-all shadow-lg shadow-brand-500/25 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Uploading &amp; Profiling...
                </>
              ) : (
                <>
                  <CheckCircle className="w-3.5 h-3.5" />
                  Upload Dataset
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
