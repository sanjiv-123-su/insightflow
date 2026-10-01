import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { datasetService } from '../services/datasetService';
import { getErrorMessage } from '../services/api';
import type {
  Dataset,
  DatasetProfileResponse,
  DataQualityResponse,
} from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import {
  BarChart3,
  ArrowLeft,
  AlertTriangle,
  Layers,
  FileSpreadsheet,
  FileText,
  Search,
} from 'lucide-react';


export const DatasetProfilePage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [profile, setProfile] = useState<DatasetProfileResponse | null>(null);
  const [quality, setQuality] = useState<DataQualityResponse | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchColumn, setSearchColumn] = useState('');

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [ds, prof, qual] = await Promise.all([
        datasetService.getDatasetById(id),
        datasetService.getDatasetProfile(id),
        datasetService.getDatasetQuality(id),
      ]);
      setDataset(ds);
      setProfile(prof);
      setQuality(qual);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return <LoadingSpinner fullPage message="Loading dataset profiling & quality metrics..." />;
  }

  if (!dataset || !profile) {
    return (
      <div className="space-y-4">
        <Link
          to="/datasets"
          className="inline-flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 font-medium"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Datasets
        </Link>
        <ErrorAlert
          title="Profile Not Found"
          message={error || 'Could not load data profile for this dataset.'}
          onRetry={loadData}
        />
      </div>
    );
  }

  const { summary, columns, warnings } = profile;

  const filteredColumns = columns.filter((c) =>
    c.column_name.toLowerCase().includes(searchColumn.toLowerCase())
  );

  const qualityScore = summary.overall_data_quality_score;
  const qualityColor =
    qualityScore >= 85
      ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
      : qualityScore >= 65
      ? 'text-amber-400 border-amber-500/30 bg-amber-500/10'
      : 'text-rose-400 border-rose-500/30 bg-rose-500/10';

  const qualityRating =
    qualityScore >= 85 ? 'Excellent' : qualityScore >= 65 ? 'Moderate' : 'Poor Quality';

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Link to="/datasets" className="hover:text-slate-200 transition-colors">
          Datasets
        </Link>
        <span>/</span>
        <Link to={`/datasets/${dataset.id}`} className="hover:text-slate-200 transition-colors">
          {dataset.name}
        </Link>
        <span>/</span>
        <span className="text-slate-200 font-medium">Profile &amp; Quality</span>
      </div>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center shrink-0">
            {dataset.file_type === 'csv' ? (
              <FileText className="w-6 h-6" />
            ) : (
              <FileSpreadsheet className="w-6 h-6" />
            )}
          </div>
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-white">
              Data Profile: {dataset.name}
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 mt-0.5">
              Automated pandas statistical profiling, data typing, and null check analysis
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to={`/datasets/${dataset.id}`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md shadow-brand-500/20 transition-all"
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>View Analytics</span>
          </Link>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadData} />}

      {/* Quality Summary & KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Quality Score Card */}
        <div className="glass-panel rounded-2xl p-5 sm:col-span-2 lg:col-span-1 border border-slate-800 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Quality Score
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${qualityColor}`}>
              {qualityRating}
            </span>
          </div>
          <div className="my-3">
            <span className="text-3xl font-bold text-white">{qualityScore.toFixed(1)}</span>
            <span className="text-sm font-semibold text-slate-400">/100</span>
          </div>
          <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                qualityScore >= 85
                  ? 'bg-emerald-500'
                  : qualityScore >= 65
                  ? 'bg-amber-500'
                  : 'bg-rose-500'
              }`}
              style={{ width: `${Math.min(qualityScore, 100)}%` }}
            />
          </div>
        </div>

        {/* Total Rows */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Total Rows
          </span>
          <div className="my-2 text-2xl font-bold text-white">
            {summary.row_count.toLocaleString()}
          </div>
          <span className="text-[11px] text-slate-400">Observed records</span>
        </div>

        {/* Total Columns */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Total Columns
          </span>
          <div className="my-2 text-2xl font-bold text-white">
            {summary.column_count}
          </div>
          <span className="text-[11px] text-slate-400">Analyzed attributes</span>
        </div>

        {/* Duplicate Rows */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Duplicate Rows
          </span>
          <div className="my-2 text-2xl font-bold text-white">
            {summary.duplicate_rows.toLocaleString()}
          </div>
          <span className="text-[11px] text-slate-400">
            {summary.duplicate_rows === 0 ? 'No duplicates detected' : 'Identical records'}
          </span>
        </div>

        {/* Missing Values */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Missing Values
          </span>
          <div className="my-2 text-2xl font-bold text-white">
            {summary.total_missing_values.toLocaleString()}
          </div>
          <span className="text-[11px] text-slate-400">Total null cells</span>
        </div>
      </div>

      {/* Quality Breakdown Metrics (if returned from /quality) */}
      {quality?.metrics && (
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">
            Quality Dimension Breakdown
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-300 font-medium">Completeness</span>
                <span className="font-bold text-white font-mono">
                  {quality.metrics.completeness_score.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-brand-500 h-full rounded-full"
                  style={{ width: `${quality.metrics.completeness_score}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-300 font-medium">Uniqueness</span>
                <span className="font-bold text-white font-mono">
                  {quality.metrics.uniqueness_score.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-cyan-500 h-full rounded-full"
                  style={{ width: `${quality.metrics.uniqueness_score}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-300 font-medium">Validity</span>
                <span className="font-bold text-white font-mono">
                  {quality.metrics.validity_score.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full"
                  style={{ width: `${quality.metrics.validity_score}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Warnings & Anomalies Banner */}
      {(warnings.completely_empty_columns.length > 0 ||
        warnings.high_null_columns.length > 0 ||
        warnings.duplicate_rows_count > 0 ||
        warnings.invalid_values_count > 0) && (
        <div className="rounded-2xl border border-amber-500/20 bg-amber-950/20 p-5 backdrop-blur-md space-y-2">
          <div className="flex items-center gap-2 text-amber-400 font-semibold text-sm">
            <AlertTriangle className="w-4 h-4" />
            <span>Data Warnings &amp; Detected Anomalies</span>
          </div>
          <ul className="text-xs text-amber-200/80 space-y-1 list-disc list-inside">
            {warnings.completely_empty_columns.length > 0 && (
              <li>
                Completely empty columns ({warnings.completely_empty_columns.length}):{' '}
                <strong className="text-amber-300">
                  {warnings.completely_empty_columns.join(', ')}
                </strong>
              </li>
            )}
            {warnings.high_null_columns.length > 0 && (
              <li>
                High-null columns (&gt;50% missing):{' '}
                <strong className="text-amber-300">{warnings.high_null_columns.join(', ')}</strong>
              </li>
            )}
            {warnings.duplicate_rows_count > 0 && (
              <li>
                Found{' '}
                <strong className="text-amber-300">{warnings.duplicate_rows_count}</strong> duplicate
                rows. Consider deduplicating before exporting.
              </li>
            )}
            {warnings.invalid_values_count > 0 && (
              <li>
                Found <strong className="text-amber-300">{warnings.invalid_values_count}</strong>{' '}
                potentially invalid or out-of-range cell values.
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Column-level Profiles Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-brand-400" />
              Column-Level Profiles
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Detailed statistics, data types, null shares, and value samples
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchColumn}
              onChange={(e) => setSearchColumn(e.target.value)}
              placeholder="Filter columns..."
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-xs text-white placeholder:text-slate-400 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-700/80 text-slate-400">
                <th className="pb-3 font-semibold">Column</th>
                <th className="pb-3 font-semibold">Type</th>
                <th className="pb-3 font-semibold text-right">Null Count</th>
                <th className="pb-3 font-semibold text-right">Null %</th>
                <th className="pb-3 font-semibold text-right">Distinct</th>
                <th className="pb-3 font-semibold text-right">Min / Max</th>
                <th className="pb-3 font-semibold text-right">Mean / Median</th>
                <th className="pb-3 font-semibold pl-4">Samples</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredColumns.map((col) => {
                const isHighNull = col.null_percentage > 50;
                return (
                  <tr key={col.column_name} className="hover:bg-slate-800/40 transition-colors">
                    {/* Name */}
                    <td className="py-3.5 font-semibold text-slate-200">
                      <span className="font-mono bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">
                        {col.column_name}
                      </span>
                    </td>

                    {/* Detected Type */}
                    <td className="py-3.5">
                      <span className="text-[11px] px-2 py-0.5 rounded bg-slate-900 text-slate-300 font-mono border border-slate-800">
                        {col.detected_data_type}
                      </span>
                    </td>

                    {/* Null Count */}
                    <td className="py-3.5 text-right font-mono text-slate-300">
                      {col.null_count.toLocaleString()}
                    </td>

                    {/* Null Percentage */}
                    <td className="py-3.5 text-right font-mono">
                      <span
                        className={`${
                          isHighNull
                            ? 'text-rose-400 font-bold'
                            : col.null_percentage > 0
                            ? 'text-amber-400'
                            : 'text-emerald-400'
                        }`}
                      >
                        {col.null_percentage.toFixed(1)}%
                      </span>
                    </td>

                    {/* Unique count */}
                    <td className="py-3.5 text-right font-mono text-slate-300">
                      {col.unique_count.toLocaleString()}
                    </td>

                    {/* Min / Max */}
                    <td className="py-3.5 text-right font-mono text-slate-400">
                      {col.minimum !== null && col.minimum !== undefined ? (
                        <span>
                          {String(col.minimum)} &rarr; {String(col.maximum)}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* Mean / Median */}
                    <td className="py-3.5 text-right font-mono text-slate-400">
                      {col.mean !== null && col.mean !== undefined ? (
                        <span>
                          {col.mean.toFixed(2)} / {col.median?.toFixed(2) ?? '—'}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* Sample Values */}
                    <td className="py-3.5 pl-4">
                      <div className="flex items-center gap-1.5 flex-wrap max-w-xs">
                        {col.sample_values.slice(0, 3).map((val, idx) => (
                          <span
                            key={idx}
                            className="inline-block max-w-[90px] truncate text-[10px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/60 font-mono"
                            title={String(val)}
                          >
                            {val === null ? 'null' : String(val)}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
