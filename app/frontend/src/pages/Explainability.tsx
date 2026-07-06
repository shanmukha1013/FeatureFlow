import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Explainability = () => {
  const [selectedModel, setSelectedModel] = useState<string>('');
  
  const { data: models, isLoading: modelsLoading } = useQuery({
    queryKey: ['models_explain'],
    queryFn: () => apiClient.get('/management/models').then(res => res.data.items),
  });

  const { data: importance, isLoading: impLoading } = useQuery({
    queryKey: ['model_importance', selectedModel],
    queryFn: () => apiClient.get(`/management/models/${selectedModel}/importance`).then(res => res.data),
    enabled: !!selectedModel,
  });

  if (modelsLoading) return <LoadingSpinner message="Loading models..." />;

  return (
    <div className="space-y-6 animate-in fade-in pb-12 max-w-6xl">
      <PageHeader title="Explainable AI (XAI)" subtitle="Global Feature Importance & Local Prediction Explanations." />

      <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Global Explanations</h2>
        
        <div>
          <label className="block text-xs font-medium text-muted uppercase mb-2">Select Model Artifact</label>
          <select 
            className="w-full bg-[#0a0a0a] border border-border rounded-md p-2.5 text-sm text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
            value={selectedModel}
            onChange={e => setSelectedModel(e.target.value)}
          >
            <option value="">-- Select a Trained Model --</option>
            {models?.map((m: any) => (
              <option key={m.model_id} value={m.model_id}>{m.model_id} ({m.algorithm})</option>
            ))}
          </select>
        </div>

        {impLoading && <LoadingSpinner message="Generating global explanation..." />}
        
        {importance && importance.feature_importance && Object.keys(importance.feature_importance).length > 0 && (
          <div className="space-y-4 pt-4 border-t border-border/50">
            <h3 className="text-sm font-semibold text-white">Feature Importance Ranking</h3>
            <div className="space-y-2">
              {Object.entries(importance.feature_importance)
                .sort((a: any, b: any) => b[1] - a[1])
                .slice(0, 10)
                .map(([feat, score]: [string, any]) => (
                <div key={feat} className="flex items-center gap-4">
                  <div className="w-48 text-xs font-mono text-muted truncate" title={feat}>{feat}</div>
                  <div className="flex-1 bg-[#0a0a0a] rounded-full h-3 overflow-hidden border border-border/50">
                    <div 
                      className="bg-primary h-full rounded-full" 
                      style={{ width: `${Math.min(100, (score * 100))}%` }}
                    />
                  </div>
                  <div className="w-16 text-xs text-right text-muted">{(score * 100).toFixed(1)}%</div>
                </div>
              ))}
            </div>
            
            <p className="text-xs text-muted italic mt-4">
              Note: For decision trees and random forests, this represents native Gini/Entropy importance. For linear models, this represents absolute normalized coefficients.
            </p>
          </div>
        )}
        
        {importance && Object.keys(importance.feature_importance || {}).length === 0 && (
          <div className="text-sm text-muted">No feature importance data available for this algorithm.</div>
        )}
      </div>
      
      <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Local Explanations</h2>
        <p className="text-sm text-muted">
          Local Explanations are automatically generated on-the-fly for every live prediction.
          To see local explanations, visit the <a href="/inference" className="text-primary hover:underline">Inference Playground</a> and execute a request. 
          The engine will natively return Top Contributors, Positive Drivers, and Negative Drivers per prediction.
        </p>
      </div>
    </div>
  );
};
