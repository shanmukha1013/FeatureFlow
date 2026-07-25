// In-memory storage for the access token to avoid XSS vulnerabilities
// associated with localStorage. Refresh tokens are stored in localStorage temporarily.

let inMemoryAccessToken: string | null = null;

export const setAccessToken = (token: string | null) => {
  inMemoryAccessToken = token;
};

export const getAccessToken = (): string | null => {
  return inMemoryAccessToken;
};

export const setRefreshToken = (token: string | null) => {
  if (token) {
    localStorage.setItem('featureflow_refresh_token', token);
  } else {
    localStorage.removeItem('featureflow_refresh_token');
  }
};

export const getRefreshToken = (): string | null => {
  return localStorage.getItem('featureflow_refresh_token');
};

export const clearTokens = () => {
  setAccessToken(null);
  setRefreshToken(null);
};
