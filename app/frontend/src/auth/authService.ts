import { apiClient } from '../api/client';
import { UserProfile, TokenResponse } from './authTypes';

export const authService = {
  login: async (username: string, password: string):Promise<TokenResponse> => {
    const response = await apiClient.post('/auth/login', { username, password });
    return response.data;
  },

  refresh: async (refresh_token: string):Promise<TokenResponse> => {
    const response = await apiClient.post('/auth/refresh', { refresh_token });
    return response.data;
  },

  me: async ():Promise<UserProfile> => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  logout: async ():Promise<void> => {
    try {
      await apiClient.post('/auth/logout');
    } catch (e) {
      console.warn("Logout failed on server, continuing local logout.", e);
    }
  }
};
