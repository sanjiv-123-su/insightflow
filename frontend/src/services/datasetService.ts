import { apiClient } from './api';
import type {
  Dataset,
  DatasetUploadResponse,
  DatasetProfileResponse,
  DataQualityResponse,
} from '../types';


export const datasetService = {
  async getDatasets(): Promise<Dataset[]> {
    const response = await apiClient.get<Dataset[]>('/datasets');
    return response.data;
  },

  async getDatasetById(id: string): Promise<Dataset> {
    const response = await apiClient.get<Dataset>(`/datasets/${id}`);
    return response.data;
  },

  async uploadDataset(file: File, name?: string): Promise<DatasetUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (name) {
      formData.append('name', name);
    }

    const response = await apiClient.post<DatasetUploadResponse>('/datasets/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getDatasetProfile(id: string): Promise<DatasetProfileResponse> {
    const response = await apiClient.get<DatasetProfileResponse>(`/datasets/${id}/profile`);
    return response.data;
  },

  async getDatasetQuality(id: string): Promise<DataQualityResponse> {
    const response = await apiClient.get<DataQualityResponse>(`/datasets/${id}/quality`);
    return response.data;
  },
};
