import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { datasetService } from '../services/datasetService';
import { analyticsService } from '../services/analyticsService';
import { aiInsightsService } from '../services/aiInsightsService';
import { getErrorMessage } from '../services/api';
import type {
  Dataset,
  DatasetAnalyticsResponse,
  DetectedColumnMapping,
  ColumnMappingInput,
  AiInsightsResponse,
} from '../types';

import { KpiCard } from '../components/cards/KpiCard';
import { AiInsightsCard } from '../components/insights/AiInsightsCard';
import { RevenueTrendChart } from '../components/charts/RevenueTrendChart';
import { CategoryDonutChart } from '../components/charts/CategoryDonutChart';
import { RegionBarChart } from '../components/charts/RegionBarChart';
import { TopProductsTable } from '../components/charts/TopProductsTable';
import { TopCustomersTable } from '../components/charts/TopCustomersTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import {
  DollarSign,
  ShoppingCart,
  Users,
  CreditCard,
  SlidersHorizontal,
  FileSearch,
  ArrowLeft,
  CheckCircle,
  FileSpreadsheet,
  FileText,
  Save,
  RotateCcw,
  Terminal,
} from 'lucide-react';

export const DatasetDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [analytics, setAnalytics] = useState<DatasetAnalyticsResponse | null>(null);
  const [mapping, setMapping] = useState<DetectedColumnMapping | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUpdatingMapping, setIsUpdatingMapping] = useState(false);
  const [showMappingPanel, setShowMappingPanel] = useState(false);
  const [mappingSuccess, setMappingSuccess] = useState(false);

  // Form state for column mapping
  const [mappingForm, setMappingForm] = useState<ColumnMappingInput>({});

  // AI Insights state (generated only after normal analytics is ready)
  const [aiInsights, setAiInsights] = useState<AiInsightsResponse | null>(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [isRegeneratingInsights, setIsRegeneratingInsights] = useState(false);

  const loadData = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [ds, an, map] = await Promise.all([
        datasetService.getDatasetById(id),
        analyticsService.getDatasetAnalytics(id),
        analyticsService.getColumnMapping(id),
      ]);
      setDataset(ds);
      setAnalytics(an);
      setMapping(map);
      setMappingForm({
        revenue_column: map.revenue_column || '',
        order_id_column: map.order_id_column || '',
        customer_column: map.customer_column || '',
        date_column: map.date_column || '',
        category_column: map.category_column || '',
        region_column: map.region_column || '',
        product_column: map.product_column || '',
      });

      // Load AI Insights only after normal analytics is ready
      if (an && an.kpis && an.kpis.total_revenue > 0) {
        setLoadingInsights(true);
        aiInsightsService
          .getAiInsights(id)
          .then((res) => setAiInsights(res))
          .catch((err) => console.log('AI Insights loading info:', err))
          .finally(() => setLoadingInsights(false));
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleRegenerateInsights = async () => {
    if (!id) return;
    setIsRegeneratingInsights(true);
    try {
      const fresh = await aiInsightsService.regenerateAiInsights(id);
      setAiInsights(fresh);
    } catch (err) {
      console.error('Failed to regenerate AI insights:', err);
    } finally {
      setIsRegeneratingInsights(false);
    }
  };

  const handleUpdateMapping = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    setIsUpdatingMapping(true);
    setError(null);
    setMappingSuccess(false);

    try {
      const cleanForm: ColumnMappingInput = {};
      Object.entries(mappingForm).forEach(([k, v]) => {
        if (v && v.trim() !== '') {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (cleanForm as any)[k] = v;
        }
      });

      const updated = await analyticsService.updateDatasetAnalytics(id, cleanForm);
      setAnalytics(updated);
      const updatedMapping = await analyticsService.getColumnMapping(id);
      setMapping(updatedMapping);
      setMappingSuccess(true);
      setTimeout(() => setMappingSuccess(false), 3000);

      // Re-run AI insights against updated analytics
      if (updated && updated.kpis && updated.kpis.total_revenue > 0) {
        setLoadingInsights(true);
        aiInsightsService
          .regenerateAiInsights(id)
          .then((res) => setAiInsights(res))
          .catch((err) => console.log('AI insights update info:', err))
          .finally(() => setLoadingInsights(false));
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsUpdatingMapping(false);
    }
  };

  if (loading) {
    return <LoadingSpinner fullPage message="Loading dataset analytics & mapping..." />;
  }

  if (!dataset) {
    return (
      <div className="space-y-4">
        <Link
          to="/datasets"
          className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Datasets
        </Link>
        <ErrorAlert
          title="Dataset Not Found"
          message={error || 'Could not locate dataset or access is unauthorized.'}
        />
      </div>
    );
  }

  const allColumns = Array.from(
    new Set([
      ...(mapping?.available_numeric_columns || []),
      ...(mapping?.available_categorical_columns || []),
      ...(mapping?.available_date_columns || []),
    ])
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link to="/datasets" className="hover:text-slate-900 transition-colors">
          Datasets
        </Link>
        <span>/</span>
        <span className="text-slate-900 font-medium">{dataset.name}</span>
      </div>

      {/* Header Bar */}
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
              {dataset.name}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
              {dataset.original_filename} &bull; {dataset.row_count?.toLocaleString()} rows &bull;{' '}
              {dataset.column_count} columns &bull; {(dataset.file_size / (1024 * 1024)).toFixed(2)} MB
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => setShowMappingPanel(!showMappingPanel)}
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
              showMappingPanel
                ? 'bg-blue-50 border-blue-200 text-blue-700'
                : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-700 hover:text-slate-900 shadow-sm'
            }`}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
            <span>{showMappingPanel ? 'Hide Mapping' : 'Configure Columns'}</span>
          </button>

          <Link
            to={`/datasets/${dataset.id}/sql`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 text-xs font-semibold transition-colors"
          >
            <Terminal className="w-3.5 h-3.5 text-blue-600" />
            <span>SQL Explorer</span>
          </Link>

          <Link
            to={`/datasets/${dataset.id}/profile`}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold transition-colors shadow-sm"
          >
            <FileSearch className="w-3.5 h-3.5" />
            <span>Data Profile &amp; Quality</span>
          </Link>
        </div>
      </div>

      {error && <ErrorAlert message={error} onRetry={loadData} />}

      {/* Column Mapping Configuration Panel */}
      {showMappingPanel && (
        <div className="glass-panel rounded-2xl p-6 border border-slate-200 shadow-sm space-y-4 animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200">
            <div>
              <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-blue-600" />
                Column Mapping Configuration
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Override auto-detected columns to fine-tune KPI, regional, and category calculations
              </p>
            </div>
            {mappingSuccess && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-medium border border-emerald-200">
                <CheckCircle className="w-3.5 h-3.5" /> Saved &amp; Recomputed
              </span>
            )}
          </div>

          <form onSubmit={handleUpdateMapping} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
              {/* Revenue */}
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Revenue / Sales Column
                </label>
                <select
                  value={mappingForm.revenue_column || ''}
                  onChange={(e) =>
                    setMappingForm({ ...mappingForm, revenue_column: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 font-mono"
                >
                  <option value="">(Auto-detect)</option>
                  {allColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Order ID */}
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Order / Transaction ID
                </label>
                <select
                  value={mappingForm.order_id_column || ''}
                  onChange={(e) =>
                    setMappingForm({ ...mappingForm, order_id_column: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 font-mono"
                >
                  <option value="">(Auto-detect)</option>
                  {allColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Customer */}
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Customer Column
                </label>
                <select
                  value={mappingForm.customer_column || ''}
                  onChange={(e) =>
                    setMappingForm({ ...mappingForm, customer_column: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 font-mono"
                >
                  <option value="">(Auto-detect)</option>
                  {allColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Date Column
                </label>
                <select
                  value={mappingForm.date_column || ''}
                  onChange={(e) =>
                    setMappingForm({ ...mappingForm, date_column: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 font-mono"
                >
                  <option value="">(Auto-detect)</option>
                  {allColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Category */}
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Category Column
                </label>
                <select
                  value={mappingForm.category_column || ''}
                  onChange={(e) =>
                    setMappingForm({ ...mappingForm, category_column: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 font-mono"
                >
                  <option value="">(Auto-detect)</option>
                  {allColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Region */}
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Region Column
                </label>
                <select
                  value={mappingForm.region_column || ''}
                  onChange={(e) =>
                    setMappingForm({ ...mappingForm, region_column: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 font-mono"
                >
                  <option value="">(Auto-detect)</option>
                  {allColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>

              {/* Product */}
              <div>
                <label className="block font-semibold uppercase tracking-wider text-slate-600 mb-1">
                  Product Column
                </label>
                <select
                  value={mappingForm.product_column || ''}
                  onChange={(e) =>
                    setMappingForm({ ...mappingForm, product_column: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 font-mono"
                >
                  <option value="">(Auto-detect)</option>
                  {allColumns.map((col) => (
                    <option key={col} value={col}>
                      {col}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200">
              <button
                type="button"
                onClick={() => {
                  if (mapping) {
                    setMappingForm({
                      revenue_column: mapping.revenue_column || '',
                      order_id_column: mapping.order_id_column || '',
                      customer_column: mapping.customer_column || '',
                      date_column: mapping.date_column || '',
                      category_column: mapping.category_column || '',
                      region_column: mapping.region_column || '',
                      product_column: mapping.product_column || '',
                    });
                  }
                }}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reset
              </button>

              <button
                type="submit"
                disabled={isUpdatingMapping}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs shadow-sm disabled:opacity-50 cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                {isUpdatingMapping ? 'Recomputing...' : 'Apply & Recompute'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Analytics KPI Cards */}
      {analytics && (
        <div className="space-y-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            <KpiCard
              title="Total Revenue"
              value={analytics.kpis.total_revenue}
              format="currency"
              change={analytics.kpis.growth_percentage}
              icon={<DollarSign className="w-5 h-5 text-blue-600" />}
              colorScheme="indigo"
              changePeriod={
                analytics.growth_summary
                  ? `vs ${analytics.growth_summary.previous_period}`
                  : 'period growth'
              }
            />

            <KpiCard
              title="Total Orders"
              value={analytics.kpis.total_orders}
              format="number"
              icon={<ShoppingCart className="w-5 h-5 text-emerald-600" />}
              colorScheme="emerald"
              subtitle={
                analytics.column_mapping.order_id_column
                  ? `Mapped to ${analytics.column_mapping.order_id_column}`
                  : 'Total records'
              }
            />

            <KpiCard
              title="Unique Customers"
              value={analytics.kpis.unique_customers}
              format="number"
              icon={<Users className="w-5 h-5 text-sky-600" />}
              colorScheme="cyan"
              subtitle={
                analytics.column_mapping.customer_column
                  ? `Mapped to ${analytics.column_mapping.customer_column}`
                  : 'No customer column'
              }
            />

            <KpiCard
              title="Average Order Value"
              value={analytics.kpis.average_order_value}
              format="currency"
              icon={<CreditCard className="w-5 h-5 text-indigo-600" />}
              colorScheme="purple"
              subtitle="Revenue per transaction"
            />
          </div>

          {/* AI Natural Language Insights (Grounded in Verified Analytics) */}
          <AiInsightsCard
            insights={aiInsights}
            loading={loadingInsights}
            onRegenerate={handleRegenerateInsights}
            isRegenerating={isRegeneratingInsights}
          />

          {/* Charts Row 1 */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <RevenueTrendChart
                data={analytics.revenue_by_month}
                title="Revenue Trend"
                subtitle={
                  analytics.column_mapping.date_column
                    ? `Monthly performance mapped from ${analytics.column_mapping.date_column}`
                    : 'Monthly revenue performance'
                }
              />
            </div>
            <div>
              <CategoryDonutChart
                data={analytics.revenue_by_category}
                title="Revenue by Category"
                subtitle={
                  analytics.column_mapping.category_column
                    ? `Grouped by ${analytics.column_mapping.category_column}`
                    : 'Category distribution'
                }
              />
            </div>
          </div>

          {/* Charts Row 2 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div>
              <RegionBarChart
                data={analytics.revenue_by_region}
                title="Revenue by Region"
                subtitle={
                  analytics.column_mapping.region_column
                    ? `Geographic sales mapped from ${analytics.column_mapping.region_column}`
                    : 'Regional distribution'
                }
              />
            </div>
            <div>
              <TopProductsTable
                products={analytics.top_products}
                title="Top Products"
                subtitle={
                  analytics.column_mapping.product_column
                    ? `Highest revenue items from ${analytics.column_mapping.product_column}`
                    : 'Best performing products'
                }
              />
            </div>
          </div>

          {/* Top Customers */}
          {analytics.top_customers.length > 0 && (
            <div>
              <TopCustomersTable
                customers={analytics.top_customers}
                title="Top Customers"
                subtitle={
                  analytics.column_mapping.customer_column
                    ? `Highest spending accounts from ${analytics.column_mapping.customer_column}`
                    : 'Top accounts'
                }
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};
