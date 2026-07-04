import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Health = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['health'],
    queryFn: () => apiClient.get('/management/health').then(res => res.data),
    refetchInterval: 5000,
  });

  if (isLoading) return <LoadingSpinner message="Probing platform health..." />;
  if (error) return <ErrorState message="Health check failed." />;

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Platform Health" subtitle="Real-time status of all micro-components." />
      
      <div className="bg-surface border border-border rounded-lg p-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Overall Status</h2>
          <p className="text-muted text-sm mt-1">Reflects aggregated dependency statuses.</p>
        </div>
        <div className="text-xl scale-125">
          <StatusBadge status={data?.status || 'UNKNOWN'} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        {data?.dependencies && Object.entries(data.dependencies).map(([key, value]: [string, any]) => (
          <div key={key} className="bg-surface border border-border p-5 rounded-lg flex flex-col gap-3">
            <div className="flex justify-between items-start">
              <h3 className="font-semibold text-white capitalize">{key.replace('_', ' ')}</h3>
              <StatusBadge status={value.status} />
            </div>
            {value.latency_ms && (
              <p className="text-sm text-muted">Latency: <span className="font-mono text-xs text-gray-300">{value.latency_ms.toFixed(2)} ms</span></p>
            )}
            {value.message && <p className="text-xs text-muted truncate">{value.message}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};
