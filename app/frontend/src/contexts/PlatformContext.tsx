import React, { createContext, useState, useEffect, ReactNode, useContext } from 'react';
import { apiClient } from '../api/client';

interface PlatformContextType {
  models: any[];
  stats: any | null;
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

  const fetchStats = async () => {
    try {
      // Independent silent fetches with fallback
      const platformRes = await apiClient.get('/management/platform').catch(() => ({ data: {} }));
      const statsRes = await apiClient.get('/management/statistics').catch(() => ({ data: {} }));
      
      setStats({ 
        ...platformRes.data, 
        ...statsRes.data 
      });
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  };

  const fetchModels = async () => {
    try {
      const modelsRes = await apiClient.get('/management/models').catch(() => ({ data: { items: [] } }));
      setModels(modelsRes.data.items || []);
    } catch (e) {
      console.error("Failed to fetch models", e);
      setModels([]);
    }
  };

  const bootstrap = async () => {
    // Fire off fetches independently without awaiting them here
    fetchStats();
    fetchModels();
  };

  useEffect(() => {
    bootstrap();
  }, []);

  // Dashboard renders immediately, no more infinite loading screen blocks
  return (
    <PlatformContext.Provider value={{ models, stats, refreshBootstrap: bootstrap }}>
      {children}
    </PlatformContext.Provider>
  );
};
