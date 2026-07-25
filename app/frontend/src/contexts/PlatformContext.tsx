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

  const [loadingStep, setLoadingStep] = useState<number>(0);
  // 0: Init, 1: Loading User, 2: Loading Platform/Stats, 3: Loading Models, 4: Preparing Dashboard, 5: Done

  const bootstrap = async () => {
    try {
      setLoadingStep(2); // Loading Platform/Stats
      try {
        const [platformRes, statsRes] = await Promise.all([
          apiClient.get('/management/platform'),
          apiClient.get('/management/statistics')
        ]);
        setStats({ ...platformRes.data, ...statsRes.data });
      } catch (e) {
        setStats(null);
      }
      
      await new Promise(res => setTimeout(res, 400));

      setLoadingStep(3); // Loading Models
      try {
        const modelsRes = await apiClient.get('/management/models');
        setModels(modelsRes.data.items || []);
      } catch (e) {

        setModels([]);
      }

      await new Promise(res => setTimeout(res, 400));
      setLoadingStep(4); // Preparing Dashboard

      await new Promise(res => setTimeout(res, 300));
      setLoadingStep(5); // Done
    } catch (err) {
      console.error("Bootstrap failed", err);
    }
  };

  useEffect(() => {
    bootstrap();
  }, []);

  if (loadingStep < 5) {
    let message = "Loading...";
    if (loadingStep === 2) message = "Loading Platform...";
    if (loadingStep === 3) message = "Loading Models...";
    if (loadingStep === 4) message = "Preparing Dashboard...";

    return (
      <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center relative overflow-hidden">
        {/* Subtle background glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-[100px] pointer-events-none"></div>
        
        <div className="flex flex-col items-center gap-6 z-10">
          <div className="text-2xl font-bold tracking-tight text-white mb-2">FeatureFlow<span className="text-indigo-500">.</span></div>
          
          <div className="w-64 h-1.5 bg-neutral-800 rounded-full overflow-hidden relative">
            <div 
              className="absolute top-0 left-0 h-full bg-indigo-500 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${(loadingStep / 5) * 100}%` }}
            ></div>
          </div>
          
          <p className="text-sm font-medium text-neutral-400 animate-pulse">{message}</p>
        </div>
      </div>
    );
  }

  return (
    <PlatformContext.Provider value={{ models, stats, refreshBootstrap: bootstrap }}>
      {children}
    </PlatformContext.Provider>
  );
};
