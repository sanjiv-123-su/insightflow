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
          className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 font-medium"
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
      ? 'text-emerald-700 border-emerald-200 bg-emerald-50'
      : qualityScore >= 65
      ? 'text-amber-700 border-amber-200 bg-amber-50'
      : 'text-rose-700 border-rose-200 bg-rose-50';

  const qualityRating =
    qualityScore >= 85 ? 'Excellent' : qualityScore >= 65 ? 'Moderate' : 'Poor Quality';

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link to="/datasets" className="hover:text-slate-900 transition-colors">
          Datasets
        </Link>
        <span>/</span>
        <Link to={`/datasets/${dataset.id}`} className="hover:text-slate-900 transition-colors">
          {dataset.name}
        </Link>
        <span>/</span>
        <span className="text-slate-900 font-medium">Profile &amp; Quality</span>
      </div>

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-slate-200">
        <div className="flex items-start gap-3">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 flex items-center justify-center shrink-0">
            {dataset.file_type === 'csv' ? (
              <FileText className="w-6 h-6" />
            ) : (
              <FileSpreadsheet className="w-6 h-6" />
            )}
          </div>
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-slate-900">
              Data Profile: {dataset.name}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
              Automated pandas statistical profiling, data typing, and null check analysis
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            to={`/datasets/${dataset.id}`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-all"
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
        <div className="glass-panel rounded-2xl p-5 sm:col-span-2 lg:col-span-1 border border-slate-200 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Quality Score
            </span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${qualityColor}`}>
              {qualityRating}
            </span>
          </div>
          <div className="my-3">
            <span className="text-3xl font-bold text-slate-900">{qualityScore.toFixed(1)}</span>
            <span className="text-sm font-semibold text-slate-400">/100</span>
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
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
        <div className="glass-panel rounded-2xl p-5 border border-slate-200 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Total Rows
          </span>
          <div className="my-2 text-2xl font-bold text-slate-900">
            {summary.row_count.toLocaleString()}
          </div>
          <span className="text-[11px] text-slate-500">Observed records</span>
        </div>

        {/* Total Columns */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-200 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Total Columns
          </span>
          <div className="my-2 text-2xl font-bold text-slate-900">
            {summary.column_count}
          </div>
          <span className="text-[11px] text-slate-500">Analyzed attributes</span>
        </div>

        {/* Duplicate Rows */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-200 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Duplicate Rows
          </span>
          <div className="my-2 text-2xl font-bold text-slate-900">
            {summary.duplicate_rows.toLocaleString()}
          </div>
          <span className="text-[11px] text-slate-500">
            {summary.duplicate_rows === 0 ? 'No duplicates detected' : 'Identical records'}
          </span>
        </div>

        {/* Missing Values */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-200 flex flex-col justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Missing Values
          </span>
          <div className="my-2 text-2xl font-bold text-slate-900">
            {summary.total_missing_values.toLocaleString()}
          </div>
          <span className="text-[11px] text-slate-500">Total null cells</span>
        </div>
      </div>

      {/* Quality Breakdown Metrics (if returned from /quality) */}
      {quality?.metrics && (
        <div className="glass-panel rounded-2xl p-6 border border-slate-200 space-y-4">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Quality Dimension Breakdown
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-600 font-medium">Completeness</span>
                <span className="font-bold text-slate-900 font-mono">
                  {quality.metrics.completeness_score.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-blue-600 h-full rounded-full"
                  style={{ width: `${quality.metrics.completeness_score}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-600 font-medium">Uniqueness</span>
                <span className="font-bold text-slate-900 font-mono">
                  {quality.metrics.uniqueness_score.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-cyan-600 h-full rounded-full"
                  style={{ width: `${quality.metrics.uniqueness_score}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1.5">
                <span className="text-slate-600 font-medium">Validity</span>
                <span className="font-bold text-slate-900 font-mono">
                  {quality.metrics.validity_score.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-emerald-600 h-full rounded-full"
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
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-5 shadow-sm space-y-2">
          <div className="flex items-center gap-2 text-amber-800 font-semibold text-sm">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Data Warnings &amp; Detected Anomalies</span>
          </div>
          <ul className="text-xs text-amber-800/90 space-y-1 list-disc list-inside">
            {warnings.completely_empty_columns.length > 0 && (
              <li>
                Completely empty columns ({warnings.completely_empty_columns.length}):{' '}
                <strong className="text-amber-950 font-semibold">
                  {warnings.completely_empty_columns.join(', ')}
                </strong>
              </li>
            )}
            {warnings.high_null_columns.length > 0 && (
              <li>
                High-null columns (&gt;50% missing):{' '}
                <strong className="text-amber-950 font-semibold">{warnings.high_null_columns.join(', ')}</strong>
              </li>
            )}
            {warnings.duplicate_rows_count > 0 && (
              <li>
                Found{' '}
                <strong className="text-amber-950 font-semibold">{warnings.duplicate_rows_count}</strong> duplicate
                rows. Consider deduplicating before exporting.
              </li>
            )}
            {warnings.invalid_values_count > 0 && (
              <li>
                Found <strong className="text-amber-950 font-semibold">{warnings.invalid_values_count}</strong>{' '}
                potentially invalid or out-of-range cell values.
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Column-level Profiles Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              Column-Level Profiles
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
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
              className="w-full pl-9 pr-3 py-1.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-slate-600 bg-slate-50/60">
                <th className="py-2.5 px-3 font-semibold">Column</th>
                <th className="py-2.5 px-3 font-semibold">Type</th>
                <th className="py-2.5 px-3 font-semibold text-right">Null Count</th>
                <th className="py-2.5 px-3 font-semibold text-right">Null %</th>
                <th className="py-2.5 px-3 font-semibold text-right">Distinct</th>
                <th className="py-2.5 px-3 font-semibold text-right">Min / Max</th>
                <th className="py-2.5 px-3 font-semibold text-right">Mean / Median</th>
                <th className="py-2.5 px-3 font-semibold pl-4">Samples</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredColumns.map((col) => {
                const isHighNull = col.null_percentage > 50;
                return (
                  <tr key={col.column_name} className="hover:bg-slate-50 transition-colors">
                    {/* Name */}
                    <td className="py-3 px-3 font-semibold text-slate-900">
                      <span className="font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200 text-slate-800">
                        {col.column_name}
                      </span>
                    </td>

                    {/* Detected Type */}
                    <td className="py-3 px-3">
                      <span className="text-[11px] px-2 py-0.5 rounded bg-slate-50 text-slate-600 font-mono border border-slate-200">
                        {col.detected_data_type}
                      </span>
                    </td>

                    {/* Null Count */}
                    <td className="py-3 px-3 text-right font-mono text-slate-700">
                      {col.null_count.toLocaleString()}
                    </td>

                    {/* Null Percentage */}
                    <td className="py-3 px-3 text-right font-mono">
                      <span
                        className={`${
                          isHighNull
                            ? 'text-rose-600 font-bold'
                            : col.null_percentage > 0
                            ? 'text-amber-600 font-medium'
                            : 'text-emerald-600'
                        }`}
                      >
                        {col.null_percentage.toFixed(1)}%
                      </span>
                    </td>

                    {/* Unique count */}
                    <td className="py-3 px-3 text-right font-mono text-slate-700">
                      {col.unique_count.toLocaleString()}
                    </td>

                    {/* Min / Max */}
                    <td className="py-3 px-3 text-right font-mono text-slate-500">
                      {col.minimum !== null && col.minimum !== undefined ? (
                        <span>
                          {String(col.minimum)} &rarr; {String(col.maximum)}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* Mean / Median */}
                    <td className="py-3 px-3 text-right font-mono text-slate-500">
                      {col.mean !== null && col.mean !== undefined ? (
                        <span>
                          {col.mean.toFixed(2)} / {col.median?.toFixed(2) ?? '—'}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>

                    {/* Sample Values */}
                    <td className="py-3 px-3 pl-4">
                      <div className="flex items-center gap-1.5 flex-wrap max-w-xs">
                        {col.sample_values.slice(0, 3).map((val, idx) => (
                          <span
                            key={idx}
                            className="inline-block max-w-[90px] truncate text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-mono"
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
