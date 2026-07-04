import React from 'react';
import { StatusBadge } from './StatusBadge';

export const MetricCard = ({ title, value, status }: { title: string, value: string | number, status?: string }) => {
  return (
    <div className="bg-surface border border-border p-6 rounded-lg flex flex-col gap-3 transition-colors hover:border-white/20">
      <h3 className="text-muted text-sm font-medium">{title}</h3>
      <div className="flex items-end justify-between">
        <span className="text-3xl font-semibold text-white tracking-tight">{value}</span>
        {status && <StatusBadge status={status} />}
      </div>
    </div>
  );
};
