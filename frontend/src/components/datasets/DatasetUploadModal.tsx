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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-in fade-in duration-200">
      <div className="w-full max-w-lg rounded-2xl bg-white p-6 sm:p-7 shadow-xl relative border border-slate-200">
        <button
          onClick={onClose}
          disabled={isUploading}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200/80 flex items-center justify-center text-blue-600 shadow-2xs">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900">Upload New Dataset</h3>
            <p className="text-xs text-slate-500">Supported formats: CSV or XLSX up to 50MB</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
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
                ? 'border-blue-600 bg-blue-50/50'
                : file
                ? 'border-emerald-300 bg-emerald-50/30'
                : 'border-slate-300 hover:border-slate-400 bg-slate-50/70 hover:bg-slate-50'
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
                <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center mb-2">
                  {file.name.endsWith('.csv') ? (
                    <FileText className="w-6 h-6" />
                  ) : (
                    <FileSpreadsheet className="w-6 h-6" />
                  )}
                </div>
                <p className="text-sm font-semibold text-slate-900 truncate max-w-xs">{file.name}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB &bull; Ready to upload
                </p>
                <span className="text-[11px] text-blue-600 mt-2 font-medium hover:underline">
                  Click or drop to replace
                </span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-500 flex items-center justify-center mb-2">
                  <UploadCloud className="w-6 h-6 text-blue-600" />
                </div>
                <p className="text-sm font-medium text-slate-700">
                  Drag and drop your file here, or{' '}
                  <span className="text-blue-600 font-semibold">browse</span>
                </p>
                <p className="text-xs text-slate-500 mt-1">Accepts .csv and .xlsx files</p>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
              Dataset Name (Optional)
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q3 Sales & Orders"
              className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-slate-900 text-sm focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 placeholder:text-slate-400 shadow-2xs"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isUploading}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || isUploading}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs transition-all shadow-xs hover:shadow disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
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
