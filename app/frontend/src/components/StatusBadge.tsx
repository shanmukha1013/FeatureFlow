import React from 'react';

export const StatusBadge = ({ status }: { status: string }) => {
  const s = status?.toUpperCase() || 'UNKNOWN';
  let colors = 'bg-border text-muted';
  
  if (['ACTIVE', 'SUCCESS', 'HEALTHY'].includes(s)) colors = 'bg-success/10 text-success border-success/20';
  if (['FAILED', 'ERROR', 'UNHEALTHY'].includes(s)) colors = 'bg-danger/10 text-danger border-danger/20';
  if (['WARNING', 'DEGRADED'].includes(s)) colors = 'bg-warning/10 text-warning border-warning/20';

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors}`}>
      {s}
    </span>
  );
};
