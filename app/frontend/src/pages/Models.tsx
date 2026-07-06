import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Models = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['models'],
    queryFn: () => apiClient.get('/management/models').then(res => res.data),
  });

  if (isLoading) return <LoadingSpinner message="Loading model registry..." />;
  if (error) return <ErrorState message="Could not connect to Management API." />;

  const columns = [
    { header: 'Model', accessor: (r: any) => (
      <div className="flex items-center space-x-2">
        <span className="font-mono text-xs">{r.model_id.substring(0,16)}</span>
        {r.lifecycle_state === 'ACTIVE' && <span className="px-2 py-0.5 text-xs font-bold bg-yellow-500/20 text-yellow-500 rounded-full">🏆 CHAMPION</span>}
      </div>
    ) },
    { header: 'Algorithm', accessor: 'algorithm' },
    { header: 'Dataset', accessor: (r: any) => <span className="text-muted text-xs">{r.dataset_version}</span> },
    { header: 'Version', accessor: 'model_version' },
    { header: 'Accuracy', accessor: (r: any) => <span className="text-muted">{(r.metrics?.accuracy * 100).toFixed(1) || 0}%</span> },
    { header: 'F1', accessor: (r: any) => <span className="text-muted">{(r.metrics?.f1 * 100).toFixed(1) || 0}%</span> },
    { header: 'Train Time', accessor: (r: any) => <span className="text-muted">{(r.training_duration_ms || 0).toFixed(0)} ms</span> },
    { header: 'Created', accessor: (r: any) => <span className="text-xs text-muted">{new Date(r.training_timestamp).toLocaleDateString()}</span> },
    { header: 'Status', accessor: (r: any) => <StatusBadge status={r.lifecycle_state || 'EXPERIMENTAL'} />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Model Registry" subtitle="Manage and track trained model artifacts across their lifecycle." />
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
