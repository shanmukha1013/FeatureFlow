import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { LoadingSpinner, ErrorState } from '../components/States';
import { StatusBadge } from '../components/StatusBadge';
import { DataTable } from '../components/DataTable';
import { AlertCircle, CheckCircle, TrendingUp } from 'lucide-react';

export const Drift = () => {
  const [selectedModel, setSelectedModel] = useState<string>('');
  
  const { data: models, isLoading: modelsLoading } = useQuery({
    queryKey: ['models_drift'],
    queryFn: () => apiClient.get('/management/models').then(res => res.data.items),
  });

  const { data: drift, isLoading: driftLoading } = useQuery({
    queryKey: ['drift_report', selectedModel],
    queryFn: () => apiClient.get(`/management/drift${selectedModel ? `?model_id=${selectedModel}` : ''}`).then(res => res.data),
    refetchInterval: 5000 // Poll every 5s for live drift
  });

  const { data: history } = useQuery({
    queryKey: ['drift_history'],
    queryFn: () => apiClient.get('/management/drift/history').then(res => res.data.history),
  });

  if (modelsLoading) return <LoadingSpinner message="Loading models..." />;

  const severityColor = (severity: string) => {
    switch(severity) {
      case 'CRITICAL': return 'text-danger bg-danger/10 border-danger/20';
      case 'WARNING': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/20';
      default: return 'text-success bg-success/10 border-success/20';
    }
  };

  const columns = [
    { header: 'Feature', accessor: 'feature' },
    { header: 'Drift Score (PSI)', accessor: (r: any) => <span className="font-mono">{r.drift_score.toFixed(4)}</span> },
    { header: 'Baseline Mean', accessor: (r: any) => <span className="text-muted">{r.baseline_mean.toFixed(2)}</span> },
    { header: 'Live Mean', accessor: (r: any) => <span className="text-muted">{r.live_mean.toFixed(2)}</span> },
    { header: 'Severity', accessor: (r: any) => <StatusBadge status={r.severity} /> },
  ];

  return (
    <div className="space-y-6 animate-in fade-in pb-12 max-w-6xl">
      <PageHeader title="Drift Detection" subtitle="Continuous monitoring of data and model decay in production." />

      <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Live Drift Monitor</h2>
        
        <div>
          <label className="block text-xs font-medium text-muted uppercase mb-2">Target Model</label>
          <select 
            className="w-full bg-[#0a0a0a] border border-border rounded-md p-2.5 text-sm text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
            value={selectedModel}
            onChange={e => setSelectedModel(e.target.value)}
          >
            <option value="">-- Active Champion (Default) --</option>
            {models?.map((m: any) => (
              <option key={m.model_id} value={m.model_id}>{m.model_id} ({m.algorithm})</option>
            ))}
          </select>
        </div>

        {driftLoading && <LoadingSpinner message="Analyzing live distributions..." />}
        
        {drift && (
          <div className="space-y-6 pt-4 border-t border-border/50">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className={`p-5 rounded-md border ${severityColor(drift.severity)} flex flex-col items-center justify-center text-center space-y-2`}>
                {drift.severity === 'CRITICAL' ? <AlertCircle size={32} /> : drift.severity === 'WARNING' ? <TrendingUp size={32} /> : <CheckCircle size={32} />}
                <div className="text-sm font-bold uppercase tracking-wider">{drift.severity}</div>
                <div className="text-xs opacity-80">Overall System Health</div>
              </div>
              
              <div className="p-5 rounded-md border border-border bg-[#0a0a0a] flex flex-col items-center justify-center text-center space-y-2">
                <div className="text-3xl font-mono text-white">{drift.overall_drift_score.toFixed(4)}</div>
                <div className="text-xs text-muted uppercase tracking-wider">Max PSI Score</div>
              </div>
              
              <div className="p-5 rounded-md border border-border bg-[#0a0a0a] flex flex-col items-center justify-center text-center space-y-2">
                <div className="text-3xl font-mono text-white">{drift.drifted_features.length}</div>
                <div className="text-xs text-muted uppercase tracking-wider">Drifted Features</div>
              </div>
            </div>

            <div className="bg-[#0a0a0a] border border-border rounded-md p-4">
              <h3 className="text-xs font-semibold text-white uppercase mb-3">Recommendations</h3>
              <ul className="list-disc pl-5 space-y-1">
                {drift.recommendations.map((rec: string, i: int) => (
                  <li key={i} className="text-sm text-muted">{rec}</li>
                ))}
              </ul>
            </div>

            <div>
              <h3 className="text-xs font-semibold text-white uppercase mb-3">Feature Shift Analysis</h3>
              {drift.drifted_features.length > 0 ? (
                <DataTable columns={columns} data={drift.drifted_features} />
              ) : (
                <div className="text-sm text-muted p-4 border border-dashed border-border rounded-md text-center">
                  No significant feature drift detected in the current live window.
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Drift Audit History</h2>
        {history && history.length > 0 ? (
          <div className="space-y-2">
            {history.map((h: any, i: number) => (
              <div key={i} className="text-sm p-3 border border-border bg-[#0a0a0a] rounded-md flex justify-between items-center">
                <span className="text-muted">{new Date(h.timestamp).toLocaleString()}</span>
                <span className="font-medium text-white">{h.event_name}</span>
                <span className="font-mono text-xs">{JSON.stringify(h.payload)}</span>
                <StatusBadge status={h.severity} />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted p-4 border border-dashed border-border rounded-md text-center">
            No historical drift alerts found.
          </div>
        )}
      </div>
    </div>
  );
};
