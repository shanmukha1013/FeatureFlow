import React, { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { setAccessToken, setRefreshToken, getRefreshToken, clearTokens } from './token';
import { authService } from './authService';

interface AuthContextType {
  isAuthenticated: boolean;
  isInitializing: boolean;
  login: (access_token: string, refresh_token: string) => void;
  logout: () => void;
  sessionExpired: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [sessionExpired, setSessionExpired] = useState(false);

  const logout = useCallback(async () => {
    if (isAuthenticated) {
      await authService.logout();
    }
    clearTokens();
    setIsAuthenticated(false);
    // Don't auto-set sessionExpired here, it's manually triggered on logout.
    // If they explicitly logged out, it's not "expired".
  }, [isAuthenticated]);

  const login = useCallback((access_token: string, refresh_token: string) => {
    setAccessToken(access_token);
    setRefreshToken(refresh_token);
    setIsAuthenticated(true);
    setSessionExpired(false);
  }, []);

  // Handle auth:expired event from API interceptor
  useEffect(() => {
    const handleExpired = () => {
      clearTokens();
      setIsAuthenticated(false);
      setSessionExpired(true);
    };
    window.addEventListener('auth:expired', handleExpired);
    return () => window.removeEventListener('auth:expired', handleExpired);
  }, []);

  // Initialize Auth
  useEffect(() => {
    const initAuth = async () => {
      const rt = getRefreshToken();
      if (!rt) {
        setIsInitializing(false);
        return;
      }
      try {
        const tokens = await authService.refresh(rt);
        login(tokens.access_token, tokens.refresh_token);
      } catch (err) {
        clearTokens();
      } finally {
        setIsInitializing(false);
      }
    };
    initAuth();
  }, [login]);

  return (
    <AuthContext.Provider value={{ isAuthenticated, isInitializing, login, logout, sessionExpired }}>
      {children}
    </AuthContext.Provider>
  );
};
