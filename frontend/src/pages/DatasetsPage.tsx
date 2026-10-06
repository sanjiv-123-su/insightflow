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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200/80">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-slate-900">
            Datasets
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            Manage your uploaded CSV and XLSX data files and inspect automated profiles
          </p>
        </div>

        <button
          onClick={() => setIsUploadOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs sm:text-sm transition-colors shadow-xs hover:shadow cursor-pointer self-start sm:self-auto"
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
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 text-xs sm:text-sm focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 placeholder:text-slate-400 shadow-2xs"
            />
          </div>

          <div className="text-xs text-slate-500 font-medium self-end sm:self-auto">
            Showing <span className="font-semibold text-slate-800">{filteredDatasets.length}</span> of{' '}
            <span className="font-semibold text-slate-800">{datasets.length}</span> datasets
          </div>
        </div>
      )}

      {/* Datasets Grid */}
      {datasets.length === 0 ? (
        <EmptyState
          icon={<Database className="w-8 h-8 text-blue-600" />}
          title="No Datasets Uploaded"
          description="Upload your first CSV or XLSX file to begin automated data profiling and analytics generation."
          actionText="Upload Dataset"
          onAction={() => setIsUploadOpen(true)}
        />
      ) : filteredDatasets.length === 0 ? (
        <div className="glass-panel rounded-2xl p-10 text-center">
          <p className="text-slate-500 text-sm">No datasets matched your search query "{searchQuery}".</p>
          <button
            onClick={() => setSearchQuery('')}
            className="mt-3 text-xs text-blue-600 hover:text-blue-700 font-medium cursor-pointer"
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
                className="glass-panel glass-panel-hover rounded-2xl p-6 flex flex-col justify-between border border-slate-200 hover:border-slate-300 shadow-2xs hover:shadow-xs transition-all"
              >
                <div>
                  {/* Card Header: Icon + Type Badge + Status */}
                  <div className="flex items-start justify-between gap-3 mb-4">
                    <div
                      className={`w-11 h-11 rounded-xl flex items-center justify-center ${
                        isCsv
                          ? 'bg-blue-50 text-blue-600 border border-blue-200/80'
                          : 'bg-emerald-50 text-emerald-600 border border-emerald-200/80'
                      }`}
                    >
                      {isCsv ? <FileText className="w-5 h-5" /> : <FileSpreadsheet className="w-5 h-5" />}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="uppercase text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 border border-slate-200">
                        {dataset.file_type}
                      </span>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-md capitalize ${
                          dataset.status === 'processed' || dataset.status === 'ready'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : dataset.status === 'processing'
                            ? 'bg-amber-50 text-amber-700 border border-amber-200'
                            : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {dataset.status}
                      </span>
                    </div>
                  </div>

                  {/* Title & Filename */}
                  <h3 className="text-base font-bold text-slate-900 truncate" title={dataset.name}>
                    {dataset.name}
                  </h3>
                  <p className="text-xs text-slate-500 truncate mt-0.5" title={dataset.original_filename}>
                    {dataset.original_filename}
                  </p>

                  {/* Metadata Stats */}
                  <div className="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-slate-100 text-xs">
                    <div className="flex items-center gap-1.5 text-slate-500">
                      <Layers className="w-3.5 h-3.5 text-slate-400" />
                      <span>
                        <strong className="text-slate-800">
                          {dataset.row_count !== null && dataset.row_count !== undefined
                            ? dataset.row_count.toLocaleString()
                            : '—'}
                        </strong>{' '}
                        rows
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-500">
                      <HardDrive className="w-3.5 h-3.5 text-slate-400" />
                      <span className="text-slate-800 font-medium">
                        {formatFileSize(dataset.file_size)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-500 col-span-2">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>Uploaded {formatDate(dataset.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="grid grid-cols-3 gap-2 mt-6 pt-4 border-t border-slate-100">
                  <Link
                    to={`/datasets/${dataset.id}`}
                    className="inline-flex items-center justify-center gap-1 px-2.5 py-2 rounded-xl bg-blue-50 hover:bg-blue-100/80 border border-blue-200/80 text-blue-700 text-xs font-semibold shadow-2xs transition-colors"
                  >
                    <BarChart3 className="w-3.5 h-3.5" />
                    Analytics
                  </Link>
                  <Link
                    to={`/datasets/${dataset.id}/sql`}
                    className="inline-flex items-center justify-center gap-1 px-2.5 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors"
                  >
                    <Terminal className="w-3.5 h-3.5 text-slate-500" />
                    SQL
                  </Link>
                  <Link
                    to={`/datasets/${dataset.id}/profile`}
                    className="inline-flex items-center justify-center gap-1 px-2.5 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-colors"
                  >
                    <FileSearch className="w-3.5 h-3.5 text-slate-500" />
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
