import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { datasetService } from '../services/datasetService';
import { analyticsService } from '../services/analyticsService';
import { aiInsightsService } from '../services/aiInsightsService';
import { getErrorMessage } from '../services/api';
import type { Dataset, DatasetAnalyticsResponse, AiInsightsResponse } from '../types';

import { KpiCard } from '../components/cards/KpiCard';
import { AiInsightsCard } from '../components/insights/AiInsightsCard';
import { RevenueTrendChart } from '../components/charts/RevenueTrendChart';
import { CategoryDonutChart } from '../components/charts/CategoryDonutChart';
import { RegionBarChart } from '../components/charts/RegionBarChart';
import { TopProductsTable } from '../components/charts/TopProductsTable';
import { TopCustomersTable } from '../components/charts/TopCustomersTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ErrorAlert } from '../components/common/ErrorAlert';
import { EmptyState } from '../components/common/EmptyState';
import { DatasetUploadModal } from '../components/datasets/DatasetUploadModal';
import {
  DollarSign,
  ShoppingCart,
  Users,
  CreditCard,
  Plus,
  SlidersHorizontal,
  FileSpreadsheet,
  FileSearch,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<DatasetAnalyticsResponse | null>(null);

  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // AI Insights state
  const [aiInsights, setAiInsights] = useState<AiInsightsResponse | null>(null);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [isRegeneratingInsights, setIsRegeneratingInsights] = useState(false);

  // Fetch datasets list
  const fetchDatasets = useCallback(async () => {
    setLoadingDatasets(true);
    setError(null);
    try {
      const data = await datasetService.getDatasets();
      setDatasets(data);
      if (data.length > 0) {
        // Default to the first (most recent) dataset if none selected or current not in list
        setSelectedDatasetId((prev) => {
          if (prev && data.some((d) => d.id === prev)) return prev;
          return data[0].id;
        });
      } else {
        setSelectedDatasetId(null);
        setAnalytics(null);
        setAiInsights(null);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoadingDatasets(false);
    }
  }, []);

  // Fetch analytics whenever selected dataset changes
  const fetchAnalytics = useCallback(async (datasetId: string) => {
    setLoadingAnalytics(true);
    setError(null);
    try {
      const result = await analyticsService.getDatasetAnalytics(datasetId);
      setAnalytics(result);

      // Load AI Insights in background only after normal analytics works
      if (result && result.kpis && result.kpis.total_revenue > 0) {
        setLoadingInsights(true);
        aiInsightsService
          .getAiInsights(datasetId)
          .then((res) => setAiInsights(res))
          .catch((err) => console.log('AI Insights loading info:', err))
          .finally(() => setLoadingInsights(false));
      } else {
        setAiInsights(null);
      }
    } catch (err) {
      setError(getErrorMessage(err));
      setAnalytics(null);
      setAiInsights(null);
    } finally {
      setLoadingAnalytics(false);
    }
  }, []);

  const handleRegenerateInsights = async () => {
    if (!selectedDatasetId) return;
    setIsRegeneratingInsights(true);
    try {
      const fresh = await aiInsightsService.regenerateAiInsights(selectedDatasetId);
      setAiInsights(fresh);
    } catch (err) {
      console.error('Failed to regenerate AI insights:', err);
    } finally {
      setIsRegeneratingInsights(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, [fetchDatasets]);

  useEffect(() => {
    if (selectedDatasetId) {
      fetchAnalytics(selectedDatasetId);
    }
  }, [selectedDatasetId, fetchAnalytics]);

  const selectedDataset = datasets.find((d) => d.id === selectedDatasetId);

  // 1. Initial page loading state
  if (loadingDatasets) {
    return <LoadingSpinner fullPage message="Loading datasets and analytics..." />;
  }

  // 2. Empty state: No datasets uploaded yet
  if (datasets.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">Analytics Dashboard</h1>
            <p className="text-sm text-slate-600 mt-1">
              Upload your first business dataset to automatically generate insights
            </p>
          </div>
        </div>

        <EmptyState
          title="No Datasets Found"
          description="Upload an e-commerce, sales, or business transaction CSV or XLSX file. InsightFlow will automatically detect revenues, orders, customers, and regional breakdowns."
          actionText="Upload Dataset"
          onAction={() => setIsUploadOpen(true)}
        />

        <DatasetUploadModal
          isOpen={isUploadOpen}
          onClose={() => setIsUploadOpen(false)}
          onSuccess={(newDataset) => {
            fetchDatasets().then(() => {
              setSelectedDatasetId(newDataset.id);
            });
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Bar: Title, Dataset Switcher, Quick Actions */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 pb-4 border-b border-slate-200/80">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-slate-900">
            Analytics Dashboard
          </h1>
          <p className="text-xs sm:text-sm text-slate-600 mt-1">
            Real-time business performance metrics computed directly from your uploaded data
          </p>
        </div>

        <div className="flex items-center flex-wrap gap-3">
          {/* Dataset Switcher Dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 hidden sm:inline">
              Dataset:
            </span>
            <select
              value={selectedDatasetId || ''}
              onChange={(e) => setSelectedDatasetId(e.target.value)}
              className="px-3.5 py-2 rounded-xl bg-white border border-slate-200 text-slate-800 text-xs sm:text-sm font-medium focus:outline-none focus:border-blue-600 focus:ring-2 focus:ring-blue-100 shadow-2xs cursor-pointer max-w-[220px] truncate"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name || d.original_filename}
                </option>
              ))}
            </select>
          </div>

          {selectedDatasetId && (
            <div className="flex items-center gap-2">
              <Link
                to={`/datasets/${selectedDatasetId}`}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 hover:text-slate-900 shadow-2xs transition-colors"
                title="Configure Column Mappings"
              >
                <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
                <span className="hidden sm:inline">Mapping</span>
              </Link>

              <Link
                to={`/datasets/${selectedDatasetId}/profile`}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-700 hover:text-slate-900 shadow-2xs transition-colors"
                title="View Data Profile & Quality"
              >
                <FileSearch className="w-3.5 h-3.5 text-slate-500" />
                <span className="hidden sm:inline">Profile</span>
              </Link>
            </div>
          )}

          <button
            onClick={() => setIsUploadOpen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs sm:text-sm transition-colors shadow-xs hover:shadow cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Upload Dataset</span>
          </button>
        </div>
      </div>

      {/* Dataset quick metadata badge bar */}
      {selectedDataset && (
        <div className="flex items-center flex-wrap gap-4 text-xs text-slate-600 bg-white p-3.5 rounded-xl border border-slate-200/80 shadow-2xs">
          <div className="flex items-center gap-1.5">
            <FileSpreadsheet className="w-4 h-4 text-blue-600" />
            <span className="font-semibold text-slate-900">{selectedDataset.name}</span>
            <span className="text-slate-500">({selectedDataset.original_filename})</span>
          </div>
          <span className="text-slate-300">&bull;</span>
          <div>
            Format: <span className="font-semibold text-slate-700 uppercase">{selectedDataset.file_type}</span>
          </div>
          {selectedDataset.row_count !== null && selectedDataset.row_count !== undefined && (
            <>
              <span className="text-slate-300">&bull;</span>
              <div>
                Rows: <span className="font-semibold text-slate-700">{selectedDataset.row_count.toLocaleString()}</span>
              </div>
            </>
          )}
          {selectedDataset.column_count !== null && selectedDataset.column_count !== undefined && (
            <>
              <span className="text-slate-300">&bull;</span>
              <div>
                Columns: <span className="font-semibold text-slate-700">{selectedDataset.column_count}</span>
              </div>
            </>
          )}
          {analytics?.column_mapping.revenue_column && (
            <>
              <span className="text-slate-300">&bull;</span>
              <div className="text-blue-700 bg-blue-50 px-2 py-0.5 rounded-md border border-blue-100">
                Revenue Column: <span className="font-mono font-semibold">{analytics.column_mapping.revenue_column}</span>
              </div>
            </>
          )}
        </div>
      )}

      {/* Error state */}
      {error && (
        <ErrorAlert
          title="Could not load analytics"
          message={error}
          onRetry={() => selectedDatasetId && fetchAnalytics(selectedDatasetId)}
        />
      )}

      {/* Analytics Content */}
      {loadingAnalytics ? (
        <div className="py-20">
          <LoadingSpinner message="Calculating analytics engine metrics..." size="lg" />
        </div>
      ) : analytics ? (
        <div className="space-y-8">
          {/* 1. Reusable KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Total Revenue */}
            <KpiCard
              title="Total Revenue"
              value={analytics.kpis.total_revenue}
              format="currency"
              change={analytics.kpis.growth_percentage}
              icon={<DollarSign className="w-5 h-5 text-indigo-400" />}
              colorScheme="indigo"
              changePeriod={
                analytics.growth_summary
                  ? `vs ${analytics.growth_summary.previous_period}`
                  : 'period growth'
              }
            />

            {/* Total Orders */}
            <KpiCard
              title="Total Orders"
              value={analytics.kpis.total_orders}
              format="number"
              icon={<ShoppingCart className="w-5 h-5 text-emerald-400" />}
              colorScheme="emerald"
              subtitle={
                analytics.column_mapping.order_id_column
                  ? `Mapped to ${analytics.column_mapping.order_id_column}`
                  : 'Total records'
              }
            />

            {/* Unique Customers */}
            <KpiCard
              title="Unique Customers"
              value={analytics.kpis.unique_customers}
              format="number"
              icon={<Users className="w-5 h-5 text-cyan-400" />}
              colorScheme="cyan"
              subtitle={
                analytics.column_mapping.customer_column
                  ? `Mapped to ${analytics.column_mapping.customer_column}`
                  : 'No customer column mapped'
              }
            />

            {/* Average Order Value */}
            <KpiCard
              title="Average Order Value"
              value={analytics.kpis.average_order_value}
              format="currency"
              icon={<CreditCard className="w-5 h-5 text-purple-400" />}
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

          {/* 2. Charts Section - Row 1: Revenue Trend (full or 2/3) + Category Donut (1/3) */}
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

          {/* 3. Charts Section - Row 2: Revenue by Region + Top Products + Top Customers */}
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

          {/* 4. Top Customers leaderboard if available */}
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
      ) : (
        <EmptyState
          title="No Analytics Data Available"
          description="Could not generate analytics for this dataset. Please ensure the dataset contains numeric columns or configure column mappings."
          actionText="Configure Mapping"
          onAction={() => {
            if (selectedDatasetId) {
              window.location.href = `/datasets/${selectedDatasetId}`;
            }
          }}
        />
      )}

      {/* Upload modal */}
      <DatasetUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={(newDataset) => {
          fetchDatasets().then(() => {
            setSelectedDatasetId(newDataset.id);
          });
        }}
      />
    </div>
  );
};
