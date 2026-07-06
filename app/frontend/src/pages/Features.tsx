import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Features = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['features'],
    queryFn: () => apiClient.get('/management/features').then(res => res.data),
  });

  if (isLoading) return <LoadingSpinner message="Loading feature registry..." />;
  if (error) return <ErrorState message="Could not connect to Management API." />;

  const columns = [
    { header: 'Feature Name', accessor: (r: any) => <span className="font-medium text-white">{r.name}</span> },
    { header: 'Dataset', accessor: (r: any) => <span className="text-muted">{r.source_dataset || '-'}</span> },
    { header: 'Transformation', accessor: (r: any) => <span className="text-muted">{r.transformation || '-'}</span> },
    { header: 'Type', accessor: (r: any) => <span className="text-muted">{r.feature_type || '-'}</span> },
    { header: 'Version', accessor: (r: any) => <span className="font-mono text-xs">{r.version || '1.0.0'}</span> },
    { header: 'Created', accessor: (r: any) => <span className="text-xs text-muted">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}</span> },
    { header: 'Status', accessor: (r: any) => <StatusBadge status={r.status || 'ACTIVE'} />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Feature Registry" subtitle="Reusable engineered feature definitions." />
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
