import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';
import { Play } from 'lucide-react';

export const Models = () => {
  const queryClient = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['models'],
    queryFn: () => apiClient.get('/management/models').then(res => res.data),
  });

  const retrainMutation = useMutation({
    mutationFn: () => apiClient.post('/management/retraining/start'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['models'] }),
  });

  if (isLoading) return <LoadingSpinner message="Loading model registry..." />;
  if (error) return <ErrorState message="Failed to load data." />;

  const columns = [
    { header: 'Model', accessor: (r: any) => (
      <div className="flex items-center space-x-2">
        <span className="font-mono text-xs">{r.id?.substring(0,16) || '-'}</span>
        {r.status === 'ACTIVE' && <span className="px-2 py-0.5 text-xs font-bold bg-yellow-500/20 text-yellow-500 rounded-full">🏆 CHAMPION</span>}
      </div>
    ) },
    { header: 'Algorithm', accessor: 'name' },
    { header: 'Dataset', accessor: (r: any) => <span className="text-muted text-xs">{r.dataset_version || '-'}</span> },
    { header: 'Version', accessor: 'model_version' },
    { header: 'Accuracy', accessor: (r: any) => <span className="text-muted">{(r.metrics?.accuracy * 100).toFixed(1) || 0}%</span> },
    { header: 'F1', accessor: (r: any) => <span className="text-muted">{(r.metrics?.f1 * 100).toFixed(1) || 0}%</span> },
    { header: 'Train Time', accessor: (r: any) => <span className="text-muted">{(r.training_duration_ms || 0).toFixed(0)} ms</span> },
    { header: 'Created', accessor: (r: any) => <span className="text-xs text-muted">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}</span> },
    { header: 'Status', accessor: (r: any) => <StatusBadge status={r.status || 'EXPERIMENTAL'} />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <div className="flex items-center justify-between">
        <PageHeader title="Model Registry" subtitle="Manage and track trained model artifacts across their lifecycle." />
        <button
          onClick={() => retrainMutation.mutate()}
          disabled={retrainMutation.isPending}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm transition-colors disabled:opacity-50"
        >
          {retrainMutation.isPending ? (
            <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Retraining...</>
          ) : (
            <><Play className="w-4 h-4" />Retrain</>
          )}
        </button>
      </div>
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
