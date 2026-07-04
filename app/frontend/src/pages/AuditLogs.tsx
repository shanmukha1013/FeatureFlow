import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { DataTable } from '../components/DataTable';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';

export const AuditLogs = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['audit'],
    queryFn: () => apiClient.get('/management/audit').then(res => res.data),
    refetchInterval: 5000,
  });

  if (isLoading) return <LoadingSpinner message="Loading audit logs..." />;
  if (error) return <ErrorState message="Could not connect to Management API." />;

  const columns = [
    { header: 'Timestamp', accessor: (r: any) => <span className="text-muted">{new Date(r.timestamp).toLocaleString()}</span> },
    { header: 'Component', accessor: (r: any) => <span className="font-medium">{r.component}</span> },
    { header: 'Event', accessor: 'event_name' },
    { header: 'Correlation ID', accessor: (r: any) => <span className="font-mono text-xs text-muted">{r.correlation_id?.substring(0,8) || '-'}</span> },
    { header: 'Severity', accessor: (r: any) => <StatusBadge status={r.severity} />, align: 'right' as const }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Audit Events" subtitle="Immutable traceability of platform operations." />
      <DataTable columns={columns} data={data?.items || []} />
    </div>
  );
};
