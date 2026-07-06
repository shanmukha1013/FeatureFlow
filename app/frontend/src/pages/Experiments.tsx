import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Experiments = () => {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<any>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => apiClient.get('/management/experiments').then(res => res.data),
  });

  const handleCompare = async () => {
    if (selectedIds.length < 2) return;
    try {
      const res = await apiClient.get(`/management/experiments/compare?ids=${selectedIds.join(',')}`);
      setComparison(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  if (isLoading) return <LoadingSpinner message="Loading experiments..." />;
  if (error) return <ErrorState message="Could not fetch experiments." />;

  const columns = [
    { 
      header: 'Compare', 
      accessor: (r: any) => (
        <input 
          type="checkbox" 
          checked={selectedIds.includes(r.experiment_id)} 
          onChange={() => toggleSelect(r.experiment_id)}
          className="rounded border-border text-primary focus:ring-primary bg-[#0a0a0a]"
        />
      )
    },
    { header: 'Experiment', accessor: (r: any) => <span className="font-mono text-xs">{r.experiment_id.substring(0, 16)}</span> },
    { header: 'Algorithm', accessor: 'algorithm' },
    { header: 'Dataset', accessor: (r: any) => <span className="text-muted text-xs">{r.dataset_version}</span> },
    { header: 'Accuracy', accessor: (r: any) => <span className="text-muted">{(r.metrics?.accuracy * 100).toFixed(1) || 0}%</span> },
    { header: 'Duration', accessor: (r: any) => <span className="text-muted">{(r.duration_ms / 1000).toFixed(2)}s</span> },
    { header: 'Start Time', accessor: (r: any) => <span className="text-xs text-muted">{new Date(r.start_time).toLocaleString()}</span> },
    { header: 'Tags', accessor: (r: any) => (
      <div className="flex gap-1 flex-wrap">
        {r.tags?.map((t: string) => <span key={t} className="px-1.5 py-0.5 text-[10px] bg-[#1a1a1a] text-muted rounded">{t}</span>)}
      </div>
    )},
    { header: 'Status', accessor: (r: any) => <StatusBadge status={r.lifecycle_state || 'RUNNING'} />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in pb-12">
      <div className="flex justify-between items-start">
        <PageHeader title="Experiment Tracking" subtitle="Monitor, compare, and manage MLflow-style training runs." />
        <button 
          onClick={handleCompare}
          disabled={selectedIds.length < 2}
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md font-medium text-sm disabled:opacity-50 transition-opacity"
        >
          Compare Selected ({selectedIds.length})
        </button>
      </div>
      
      <DataTable columns={columns} data={data?.items || []} />

      {comparison && (
        <div className="bg-surface border border-border rounded-lg p-6 space-y-4 mt-6">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Experiment Comparison</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {comparison.experiments.map((exp: any) => {
              const isBest = exp.experiment_id === comparison.best_experiment_id;
              return (
                <div key={exp.experiment_id} className={`p-4 rounded-md border ${isBest ? 'border-yellow-500/50 bg-yellow-500/5' : 'border-border bg-[#0a0a0a]'}`}>
                  <div className="flex justify-between items-start mb-4">
                    <div className="font-mono text-xs">{exp.experiment_id.substring(0, 16)}...</div>
                    {isBest && <span className="text-xs font-bold text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded-full">🏆 BEST</span>}
                  </div>
                  
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs text-muted uppercase">Algorithm</div>
                      <div className="text-sm font-medium">{exp.algorithm}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted uppercase">Accuracy</div>
                      <div className="text-xl font-semibold">{(exp.metrics?.accuracy * 100).toFixed(2)}%</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted uppercase">F1 Score</div>
                      <div className="text-xl font-semibold">{(exp.metrics?.f1 * 100).toFixed(2)}%</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted uppercase">Training Duration</div>
                      <div className="text-sm font-medium">{(exp.duration_ms / 1000).toFixed(2)}s</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
