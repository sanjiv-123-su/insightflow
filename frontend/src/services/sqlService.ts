import { apiClient } from './api';
import type {
  SqlQueryRequest,
  SqlQueryResponse,
  SavedQuery,
  SavedQueryCreate,
} from '../types';

export const sqlService = {
  /**
   * Execute a read-only analytical SQL query on a dataset.
   */
  async executeQuery(
    datasetId: string,
    query: string,
    limit: number = 500
  ): Promise<SqlQueryResponse> {
    const payload: SqlQueryRequest = { query, limit };
    const response = await apiClient.post<SqlQueryResponse>(
      `/datasets/${datasetId}/query`,
      payload
    );
    return response.data;
  },

  /**
   * List all queries saved for this dataset.
   */
  async getSavedQueries(datasetId: string): Promise<SavedQuery[]> {
    const response = await apiClient.get<SavedQuery[]>(
      `/datasets/${datasetId}/saved-queries`
    );
    return response.data;
  },

  /**
   * Save a new analytical query.
   */
  async saveQuery(
    datasetId: string,
    data: SavedQueryCreate
  ): Promise<SavedQuery> {
    const response = await apiClient.post<SavedQuery>(
      `/datasets/${datasetId}/saved-queries`,
      data
    );
    return response.data;
  },

  /**
   * Delete a saved query.
   */
  async deleteSavedQuery(
    datasetId: string,
    queryId: string
  ): Promise<void> {
    await apiClient.delete(`/datasets/${datasetId}/saved-queries/${queryId}`);
  },
};
