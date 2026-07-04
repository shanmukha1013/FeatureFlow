import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { LoadingSpinner, ErrorState } from '../components/States';

export const Settings = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['config'],
    queryFn: () => apiClient.get('/management/config').then(res => res.data),
  });

  const { data: sysData } = useQuery({
    queryKey: ['system'],
    queryFn: () => apiClient.get('/management/system').then(res => res.data),
  });

  if (isLoading) return <LoadingSpinner message="Loading configuration..." />;
  if (error) return <ErrorState message="Could not fetch settings." />;

  return (
    <div className="space-y-8 animate-in fade-in max-w-3xl">
      <PageHeader title="Platform Settings" subtitle="Global environment and backend configuration." />
      
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <div className="p-5 border-b border-border">
          <h3 className="text-lg font-medium text-white">System Information</h3>
        </div>
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-y-4">
            <div>
              <div className="text-xs text-muted uppercase">Python Version</div>
              <div className="text-sm font-medium text-white mt-1">{sysData?.python_version}</div>
            </div>
            <div>
              <div className="text-xs text-muted uppercase">Operating System</div>
              <div className="text-sm font-medium text-white mt-1">{sysData?.operating_system}</div>
            </div>
            <div>
              <div className="text-xs text-muted uppercase">Framework</div>
              <div className="text-sm font-medium text-white mt-1">FastAPI {sysData?.framework_version}</div>
            </div>
            <div>
              <div className="text-xs text-muted uppercase">API Version</div>
              <div className="text-sm font-medium text-white mt-1">{data?.serving_version}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <div className="p-5 border-b border-border">
          <h3 className="text-lg font-medium text-white">Backend Configuration</h3>
        </div>
        <div className="p-5 space-y-4">
          <div className="grid grid-cols-2 gap-y-4">
            <div>
              <div className="text-xs text-muted uppercase">Storage Backend</div>
              <div className="text-sm font-medium text-white mt-1">{data?.storage_backend}</div>
            </div>
            <div>
              <div className="text-xs text-muted uppercase">Monitoring Backend</div>
              <div className="text-sm font-medium text-white mt-1">{data?.monitoring_backend}</div>
            </div>
            <div>
              <div className="text-xs text-muted uppercase">Training Backend</div>
              <div className="text-sm font-medium text-white mt-1">{data?.training_backend}</div>
            </div>
            <div>
              <div className="text-xs text-muted uppercase">Inference Backend</div>
              <div className="text-sm font-medium text-white mt-1">{data?.inference_backend}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
