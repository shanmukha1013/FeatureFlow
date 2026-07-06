import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { LoadingSpinner, ErrorState } from '../components/States';
import { StatusBadge } from '../components/StatusBadge';
import { DataTable } from '../components/DataTable';
import { Play, RotateCcw } from 'lucide-react';

export const Retraining = () => {
  const queryClient = useQueryClient();
  const [selectedDataset, setSelectedDataset] = useState<string>('');

  const { data: datasets, isLoading: datasetsLoading } = useQuery({
    queryKey: ['datasets_retraining'],
    queryFn: () => apiClient.get('/management/datasets').then(res => res.data.items),
  });

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['retraining_jobs'],
    queryFn: () => apiClient.get('/management/retraining').then(res => res.data.items),
    refetchInterval: 3000
  });

  const { data: history } = useQuery({
    queryKey: ['retraining_history'],
    queryFn: () => apiClient.get('/management/retraining/history').then(res => res.data.history),
    refetchInterval: 3000
  });

  const startMutation = useMutation({
    mutationFn: (dataset_name: string) => apiClient.post('/management/retraining/start', { dataset_name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['retraining_jobs'] });
      alert("Retraining started in the background.");
    }
  });

  const rollbackMutation = useMutation({
    mutationFn: (dataset_name: string) => apiClient.post('/management/retraining/rollback', { dataset_name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['retraining_history'] });
      alert("Rollback successful. Restored previous ACTIVE champion.");
    },
    onError: (e: any) => {
      alert(`Rollback failed: ${e.response?.data?.detail || e.message}`);
    }
  });

  const columns = [
    { header: 'Job ID', accessor: (r: any) => <span className="font-mono text-xs">{r.job_id.substring(0, 20)}...</span> },
    { header: 'Dataset', accessor: 'dataset_name' },
    { header: 'Trigger', accessor: 'trigger_type' },
    { header: 'Promoted?', accessor: (r: any) => (
      r.champion_promoted ? <span className="text-success font-semibold text-xs bg-success/10 px-2 py-0.5 rounded">YES</span> : <span className="text-muted text-xs">NO</span>
    )},
    { header: 'Champion ID', accessor: (r: any) => <span className="font-mono text-xs">{r.new_champion_id || '-'}</span> },
    { header: 'Status', accessor: (r: any) => <StatusBadge status={r.status} /> },
  ];

  return (
    <div className="space-y-6 animate-in fade-in pb-12 max-w-6xl">
      <PageHeader title="Continuous Retraining" subtitle="Manage Automated CI/CD pipelines for Model Training & Promotion." />

      <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
        <div className="flex justify-between items-center">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Manual Trigger</h2>
        </div>
        
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-xs font-medium text-muted uppercase mb-2">Target Dataset</label>
            <select 
              className="w-full bg-[#0a0a0a] border border-border rounded-md p-2.5 text-sm text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
              value={selectedDataset}
              onChange={e => setSelectedDataset(e.target.value)}
            >
              <option value="">-- Select Dataset --</option>
              {datasets?.map((d: any) => (
                <option key={d.dataset_id} value={d.dataset_name}>{d.dataset_name} ({d.version})</option>
              ))}
            </select>
          </div>
          <button 
            onClick={() => startMutation.mutate(selectedDataset)}
            disabled={!selectedDataset || startMutation.isPending}
            className="bg-primary text-primary-foreground hover:bg-primary/90 px-6 py-2.5 rounded-md font-medium text-sm disabled:opacity-50 flex items-center gap-2"
          >
            <Play size={16} />
            Start Pipeline
          </button>
          
          <button 
            onClick={() => rollbackMutation.mutate(selectedDataset)}
            disabled={!selectedDataset || rollbackMutation.isPending}
            className="bg-danger/10 text-danger hover:bg-danger/20 border border-danger/20 px-6 py-2.5 rounded-md font-medium text-sm disabled:opacity-50 flex items-center gap-2"
          >
            <RotateCcw size={16} />
            Rollback Champion
          </button>
        </div>
      </div>

      <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Active & Recent Jobs</h2>
        {jobsLoading ? (
          <LoadingSpinner message="Loading jobs..." />
        ) : (
          <DataTable columns={columns} data={jobs || []} />
        )}
      </div>

      <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Retraining Audit Log</h2>
        {history && history.length > 0 ? (
          <div className="space-y-2">
            {history.map((h: any, i: number) => (
              <div key={i} className="text-sm p-3 border border-border bg-[#0a0a0a] rounded-md flex justify-between items-center">
                <span className="text-muted">{new Date(h.timestamp).toLocaleString()}</span>
                <span className="font-medium text-white">{h.event_name}</span>
                <span className="font-mono text-xs truncate max-w-lg">{JSON.stringify(h.payload)}</span>
                <StatusBadge status={h.severity} />
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted p-4 border border-dashed border-border rounded-md text-center">
            No historical logs found.
          </div>
        )}
      </div>
    </div>
  );
};
