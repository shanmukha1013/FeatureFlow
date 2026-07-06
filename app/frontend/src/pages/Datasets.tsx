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
    { header: 'Dataset Name', accessor: (r: any) => <span className="font-medium text-white">{r.dataset_name}</span> },
    { header: 'Rows', accessor: (r: any) => <span className="text-muted">{r.row_count?.toLocaleString() || 0}</span> },
    { header: 'Columns', accessor: (r: any) => <span className="text-muted">{r.column_count || 0}</span> },
    { header: 'Validation Status', accessor: (r: any) => <StatusBadge status={r.validation_status || 'PENDING'} /> },
    { header: 'Profiling Status', accessor: (r: any) => <StatusBadge status={r.profiling_status || 'PENDING'} /> },
    { header: 'Schema Status', accessor: (r: any) => <StatusBadge status={r.schema_status || 'PENDING'} /> },
    { header: 'Memory Usage', accessor: (r: any) => <span className="text-muted">{((r.estimated_memory_bytes || 0) / (1024 * 1024)).toFixed(2)} MB</span> },
    { header: 'Null %', accessor: (r: any) => <span className="text-muted">{(r.null_percentage_max || 0).toFixed(1)}%</span> },
    { header: 'Duplicates', accessor: (r: any) => <span className="text-muted">{r.duplicate_count || 0}</span> },
    { header: 'Last Profile Time', accessor: (r: any) => <span className="text-xs text-muted">{r.last_profile_time ? new Date(r.last_profile_time).toLocaleString() : 'N/A'}</span>, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Datasets" subtitle="Registered raw data sources." />
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
