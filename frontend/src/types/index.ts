// TypeScript interfaces for InsightFlow API models

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials {
  email: string;
  password: string;
}

export interface Dataset {
  id: string;
  user_id: string;
  name: string;
  original_filename: string;
  file_type: 'csv' | 'xlsx' | string;
  file_size: number;
  status: 'pending' | 'processing' | 'processed' | 'ready' | 'error' | string;
  row_count?: number | null;
  column_count?: number | null;
  created_at: string;
}

export interface DatasetUploadResponse extends Dataset {
  message: string;
}

export interface ColumnProfile {
  column_name: string;
  detected_data_type: string;
  null_count: number;
  null_percentage: number;
  unique_count: number;
  minimum?: number | string | null;
  maximum?: number | string | null;
  mean?: number | null;
  median?: number | null;
  sample_values: (string | number | boolean | null)[];
}

export interface DatasetProfileSummary {
  row_count: number;
  column_count: number;
  duplicate_rows: number;
  total_missing_values: number;
  overall_data_quality_score: number;
}

export interface ProfileWarnings {
  duplicate_rows_count: number;
  completely_empty_columns: string[];
  high_null_columns: string[];
  invalid_values_count: number;
}

export interface DatasetProfileResponse {
  dataset_id: string;
  summary: DatasetProfileSummary;
  columns: ColumnProfile[];
  warnings: ProfileWarnings;
  created_at: string;
}

export interface DataQualityBreakdown {
  completeness_score: number;
  uniqueness_score: number;
  validity_score: number;
  completely_empty_columns: string[];
  high_null_columns: string[];
}

export interface DataQualityResponse {
  id: string;
  dataset_id: string;
  quality_score: number;
  missing_values: number;
  duplicate_rows: number;
  invalid_values: number;
  created_at: string;
  metrics?: DataQualityBreakdown | null;
}

export interface KpiMetrics {
  total_revenue: number;
  total_orders: number;
  unique_customers?: number | null;
  average_order_value: number;
  growth_percentage?: number | null;
}

export interface MonthlyRevenuePoint {
  period: string;
  revenue: number;
  orders: number;
  growth_percentage?: number | null;
}

export interface CategoryRevenuePoint {
  category: string;
  revenue: number;
  orders: number;
  percentage: number;
}

export interface RegionRevenuePoint {
  region: string;
  revenue: number;
  orders: number;
  percentage: number;
}

export interface TopProductPoint {
  product: string;
  revenue: number;
  orders: number;
  units_sold?: number | null;
}

export interface TopCustomerPoint {
  customer: string;
  revenue: number;
  orders: number;
  average_spend: number;
}

export interface GrowthSummary {
  current_period: string;
  previous_period: string;
  growth_percentage: number;
  trend: 'positive' | 'negative' | 'neutral';
}

export interface DetectedColumnMapping {
  revenue_column?: string | null;
  order_id_column?: string | null;
  customer_column?: string | null;
  date_column?: string | null;
  category_column?: string | null;
  region_column?: string | null;
  product_column?: string | null;
  quantity_column?: string | null;
  detected_automatically: boolean;
  available_numeric_columns: string[];
  available_categorical_columns: string[];
  available_date_columns: string[];
}

export interface ColumnMappingInput {
  revenue_column?: string | null;
  order_id_column?: string | null;
  customer_column?: string | null;
  date_column?: string | null;
  category_column?: string | null;
  region_column?: string | null;
  product_column?: string | null;
  quantity_column?: string | null;
}

export interface DatasetAnalyticsResponse {
  dataset_id: string;
  kpis: KpiMetrics;
  revenue_by_month: MonthlyRevenuePoint[];
  revenue_by_category: CategoryRevenuePoint[];
  revenue_by_region: RegionRevenuePoint[];
  top_products: TopProductPoint[];
  top_customers: TopCustomerPoint[];
  growth_summary?: GrowthSummary | null;
  column_mapping: DetectedColumnMapping;
  created_at: string;
}

export interface ApiErrorResponse {
  detail?: string | { msg?: string }[] | Record<string, unknown>;
  message?: string;
}
