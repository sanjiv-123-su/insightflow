import { apiClient } from './api';
import type { AuthResponse, LoginCredentials, RegisterCredentials, User } from '../types';


export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', credentials);
    if (response.data.access_token) {
      localStorage.setItem('insightflow_token', response.data.access_token);
    }
    return response.data;
  },

  async register(credentials: RegisterCredentials): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', credentials);
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    localStorage.setItem('insightflow_user', JSON.stringify(response.data));
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('insightflow_token');
    localStorage.removeItem('insightflow_user');
  },

  getToken(): string | null {
    return localStorage.getItem('insightflow_token');
  },

  getStoredUser(): User | null {
    const stored = localStorage.getItem('insightflow_user');
    if (!stored) return null;
    try {
      return JSON.parse(stored) as User;
    } catch {
      return null;
    }
  },
};
