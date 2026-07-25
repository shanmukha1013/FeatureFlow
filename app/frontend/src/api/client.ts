import axios from 'axios';
import { getAccessToken } from '../auth/token';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach the access token if available
apiClient.interceptors.request.use(
  (config) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // If the request was for login or refresh itself, don't trigger a global logout event here
      const url = error.config?.url || '';
      if (!url.includes('/auth/login') && !url.includes('/auth/refresh')) {
        window.dispatchEvent(new CustomEvent('auth:expired'));
      }
    }
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  }
);
