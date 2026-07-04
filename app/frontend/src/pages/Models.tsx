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
    { header: 'Model ID', accessor: (r: any) => <span className="font-mono text-xs">{r.model_id.substring(0,8)}</span> },
    { header: 'Version', accessor: 'version' },
    { header: 'Algorithm', accessor: 'algorithm' },
    { header: 'Created', accessor: (r: any) => new Date(r.created_at).toLocaleString() },
    { header: 'Status', accessor: (r: any) => <StatusBadge status={r.lifecycle_state || 'STAGED'} />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Model Registry" subtitle="Manage and track trained model artifacts across their lifecycle." />
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
