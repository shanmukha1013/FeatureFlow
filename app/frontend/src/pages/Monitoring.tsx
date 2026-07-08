import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Monitoring = () => {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['platform-stats'],
    queryFn: () => apiClient.get('/management/statistics').then(res => res.data),
    refetchInterval: 5000,
  });

  if (isLoading) return <LoadingSpinner message="Loading monitoring data..." />;
  if (error) return <ErrorState message="Could not connect to Management API." />;

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Monitoring Metrics" subtitle="Visualizing real-time telemetry from the backend." />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface border border-border p-6 rounded-lg flex flex-col justify-center items-center h-[340px]">
          <h3 className="text-sm font-medium text-muted mb-4 uppercase">Average Prediction Latency</h3>
          <p className="text-4xl font-bold text-primary">{stats?.average_latency?.toFixed(2) || 0} ms</p>
        </div>

        <div className="bg-surface border border-border p-6 rounded-lg flex flex-col justify-center items-center h-[340px]">
          <h3 className="text-sm font-medium text-muted mb-4 uppercase">Total Predictions</h3>
          <p className="text-4xl font-bold text-emerald-500">{stats?.total_predictions?.toLocaleString() || 0}</p>
        </div>
      </div>
    </div>
  );
};
