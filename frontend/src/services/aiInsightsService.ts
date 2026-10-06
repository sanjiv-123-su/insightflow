import { apiClient } from './api';
import type { AiInsightsResponse } from '../types';

export const aiInsightsService = {
  /**
   * Fetch natural language AI insights for a dataset grounded in verified analytics.
   */
  async getAiInsights(datasetId: string, useCache: boolean = true): Promise<AiInsightsResponse> {
    const response = await apiClient.get<AiInsightsResponse>(
      `/datasets/${datasetId}/ai-insights`,
      {
        params: { use_cache: useCache },
      }
    );
    return response.data;
  },

  /**
   * Force fresh recomputation of AI insights.
   */
  async regenerateAiInsights(datasetId: string): Promise<AiInsightsResponse> {
    const response = await apiClient.post<AiInsightsResponse>(
      `/datasets/${datasetId}/ai-insights/regenerate`
    );
    return response.data;
  },
};
