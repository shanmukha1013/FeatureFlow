import React, { createContext, useState, useEffect, ReactNode, useContext } from 'react';
import { apiClient } from '../api/client';

interface PlatformContextType {
  models: any[];
  stats: any | null;
  isLoading: boolean;
  error: string | null;
  refreshBootstrap: () => Promise<void>;
}

export const PlatformContext = createContext<PlatformContextType | undefined>(undefined);

export const usePlatform = () => {
  const context = useContext(PlatformContext);
  if (context === undefined) {
    throw new Error('usePlatform must be used within a PlatformProvider');
  }
  return context;
};

export const PlatformProvider = ({ children }: { children: ReactNode }) => {
  const [models, setModels] = useState<any[]>([]);
  const [stats, setStats] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async () => {
    try {
      // Independent silent fetches with fallback
      const [platformRes, statsRes] = await Promise.all([
        apiClient.get('/management/platform').catch(() => ({ data: {} })),
        apiClient.get('/management/statistics').catch(() => ({ data: {} }))
      ]);
      
      setStats({ 
        ...platformRes.data, 
        ...statsRes.data 
      });
      setError(null);
    } catch (e) {
      console.error("[v0] Failed to fetch stats", e);
      setError('Failed to load platform stats');
    }
  };

  const fetchModels = async () => {
    try {
      const modelsRes = await apiClient.get('/management/models').catch(() => ({ data: { items: [] } }));
      setModels(modelsRes.data.items || []);
      setError(null);
    } catch (e) {
      console.error("[v0] Failed to fetch models", e);
      setModels([]);
      setError('Failed to load models');
    }
  };

  const bootstrap = async () => {
    setIsLoading(true);
    try {
      // Fire off fetches independently
      await Promise.all([fetchStats(), fetchModels()]);
    } catch (e) {
      console.error("[v0] Bootstrap error", e);
      setError('Failed to initialize platform');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    bootstrap();
  }, []);

  // Dashboard renders immediately, no more infinite loading screen blocks
  return (
    <PlatformContext.Provider value={{ models, stats, isLoading, error, refreshBootstrap: bootstrap }}>
      {children}
    </PlatformContext.Provider>
  );
};
