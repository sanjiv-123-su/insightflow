import { apiClient } from './api';
import type {
  DatasetAnalyticsResponse,
  ColumnMappingInput,
  DetectedColumnMapping,
} from '../types';


export const analyticsService = {
  async getDatasetAnalytics(datasetId: string): Promise<DatasetAnalyticsResponse> {
    const response = await apiClient.get<DatasetAnalyticsResponse>(
      `/datasets/${datasetId}/analytics`
    );
    return response.data;
  },

  async updateDatasetAnalytics(
    datasetId: string,
    mapping?: ColumnMappingInput
  ): Promise<DatasetAnalyticsResponse> {
    const response = await apiClient.post<DatasetAnalyticsResponse>(
      `/datasets/${datasetId}/analytics`,
      mapping || {}
    );
    return response.data;
  },

  async getColumnMapping(datasetId: string): Promise<DetectedColumnMapping> {
    const response = await apiClient.get<DetectedColumnMapping>(
      `/datasets/${datasetId}/analytics/mapping`
    );
    return response.data;
  },
};
