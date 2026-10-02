import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { datasetService } from '../services/datasetService';
import { getErrorMessage } from '../services/api';
import type { Dataset } from '../types';

import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { EmptyState } from '../components/common/EmptyState';
import { DatasetUploadModal } from '../components/datasets/DatasetUploadModal';
import {
  Database,
  Plus,
  Search,
  FileSpreadsheet,
  FileText,
  BarChart3,
  FileSearch,
  Calendar,
  Layers,
  HardDrive,
  Terminal,
} from 'lucide-react';

export const DatasetsPage: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const fetchDatasets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await datasetService.getDatasets();
      setDatasets(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  const filteredDatasets = datasets.filter((d) => {
    const q = searchQuery.toLowerCase();
    return (
      d.name.toLowerCase().includes(q) ||
      d.original_filename.toLowerCase().includes(q) ||
      d.file_type.toLowerCase().includes(q)
    );
  });

  const formatFileSize = (bytes: number) => {
    if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return <LoadingSpinner fullPage message="Loading datasets list..." />;
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-white">
            Datasets
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Manage your uploaded CSV and XLSX data files and inspect automated profiles
          </p>
        </div>

        <button
          onClick={() => setIsUploadOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-xs sm:text-sm transition-all shadow-lg shadow-brand-500/25 cursor-pointer self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Upload Dataset</span>
        </button>
      </div>

      {error && (
        <ErrorAlert
          title="Could not load datasets"
          message={error}
          onRetry={fetchDatasets}
        />
      )}

      {/* Search & Stats Bar */}
      {datasets.length > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search datasets..."
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs sm:text-sm focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 placeholder:text-slate-400"
            />
          </div>

          <div className="text-xs text-slate-400 font-medium self-end sm:self-auto">
            Showing <span className="font-semibold text-white">{filteredDatasets.length}</span> of{' '}
            <span className="font-semibold text-white">{datasets.length}</span> datasets
          </div>
        </div>
      )}

      {/* Datasets Grid */}
      {datasets.length === 0 ? (
        <EmptyState
          icon={<Database className="w-8 h-8 text-brand-400" />}
          title="No Datasets Uploaded"
          description="Upload your first CSV or XLSX file to begin automated data profiling and analytics generation."
          actionText="Upload Dataset"
          onAction={() => setIsUploadOpen(true)}
        />
      ) : filteredDatasets.length === 0 ? (
        <div className="glass-panel rounded-2xl p-10 text-center">
          <p className="text-slate-400 text-sm">No datasets matched your search query "{searchQuery}".</p>
          <button
            onClick={() => setSearchQuery('')}
            className="mt-3 text-xs text-brand-400 hover:text-brand-300 font-medium"
          >
            Clear Search
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDatasets.map((dataset) => {
            const isCsv = dataset.file_type.toLowerCase() === 'csv';
            return (
              <div
                key={dataset.id}
                className="glass-panel glass-panel-hover rounded-2xl p-6 flex flex-col justify-between border border-slate-800 hover:border-slate-700"
              >
                <div>
                  {/* Card Header: Icon + Type Badge + Status */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div
                      className={`w-11 h-11 rounded-xl flex items-center justify-center ${
                        isCsv
                          ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}
                    >
                      {isCsv ? <FileText className="w-5 h-5" /> : <FileSpreadsheet className="w-5 h-5" />}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="uppercase text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                        {dataset.file_type}
                      </span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-md capitalize ${
                          dataset.status === 'processed' || dataset.status === 'ready'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : dataset.status === 'processing'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {dataset.status}
                      </span>
                    </div>
                  </div>

                  {/* Title & Filename */}
                  <h3 className="text-base font-bold text-white truncate" title={dataset.name}>
                    {dataset.name}
                  </h3>
                  <p className="text-xs text-slate-400 truncate mt-0.5" title={dataset.original_filename}>
                    {dataset.original_filename}
                  </p>

                  {/* Metadata Stats */}
                  <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-800/80 text-xs">
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      <span>
                        <strong className="text-slate-200">
                          {dataset.row_count !== null && dataset.row_count !== undefined
                            ? dataset.row_count.toLocaleString()
                            : '—'}
                        </strong>{' '}
                        rows
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-slate-200 font-medium">
                        {formatFileSize(dataset.file_size)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-400 col-span-2">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>Uploaded {formatDate(dataset.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="grid grid-cols-3 gap-2 mt-6 pt-4 border-t border-slate-800/80">
                  <Link
                    to={`/datasets/${dataset.id}`}
                    className="inline-flex items-center justify-center gap-1 px-2.5 py-2 rounded-xl bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/20 text-brand-300 text-xs font-semibold transition-colors"
                  >
                    <BarChart3 className="w-3.5 h-3.5" />
                    Analytics
                  </Link>
                  <Link
                    to={`/datasets/${dataset.id}/sql`}
                    className="inline-flex items-center justify-center gap-1 px-2.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white text-xs font-semibold transition-colors"
                  >
                    <Terminal className="w-3.5 h-3.5 text-brand-400" />
                    SQL
                  </Link>
                  <Link
                    to={`/datasets/${dataset.id}/profile`}
                    className="inline-flex items-center justify-center gap-1 px-2.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-300 hover:text-white text-xs font-semibold transition-colors"
                  >
                    <FileSearch className="w-3.5 h-3.5" />
                    Profile
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload Modal */}
      <DatasetUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={() => fetchDatasets()}
      />
    </div>
  );
};
