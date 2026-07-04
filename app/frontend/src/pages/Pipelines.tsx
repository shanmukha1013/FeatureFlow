import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Pipelines = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => apiClient.get('/management/pipelines').then(res => res.data),
  });

  if (isLoading) return <LoadingSpinner message="Loading pipeline history..." />;
  if (error) return <ErrorState message="Could not connect to Management API." />;

  const columns = [
    { header: 'Pipeline Run', accessor: (r: any) => <span className="font-medium text-white">{r.pipeline_name}</span> },
    { header: 'Start Time', accessor: (r: any) => <span className="text-muted">{new Date(r.start_time).toLocaleString()}</span> },
    { header: 'Duration (ms)', accessor: (r: any) => <span className="font-mono text-xs">{r.total_duration_ms?.toFixed(2)}</span> },
    { header: 'Datasets Processed', accessor: (r: any) => Object.keys(r.dataset_reports || {}).length },
    { header: 'Status', accessor: (r: any) => <StatusBadge status={r.status} />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Pipeline Execution History" subtitle="End-to-end data processing workflows." />
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
