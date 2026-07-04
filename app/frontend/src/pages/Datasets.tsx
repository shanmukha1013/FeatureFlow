import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Datasets = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => apiClient.get('/management/datasets').then(res => res.data),
  });

  if (isLoading) return <LoadingSpinner message="Loading datasets..." />;
  if (error) return <ErrorState message="Could not connect to Management API." />;

  const columns = [
    { header: 'Dataset Name', accessor: (r: any) => <span className="font-medium text-white">{r.name || r.dataset_name}</span> },
    { header: 'Version', accessor: (r: any) => <span className="font-mono text-xs">{r.version}</span> },
    { header: 'Columns', accessor: (r: any) => r.features?.length || 0 },
    { header: 'Entity ID', accessor: (r: any) => <span className="text-muted">{r.entity_id_column}</span> },
    { header: 'Status', accessor: () => <StatusBadge status="ACTIVE" />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Datasets" subtitle="Registered raw data sources." />
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
