import React from 'react';
import { Loader2 } from 'lucide-react';

export const LoadingSpinner = ({ message = "Loading..." }: { message?: string }) => (
  <div className="flex flex-col items-center justify-center p-12 text-muted">
    <Loader2 className="w-8 h-8 animate-spin mb-4" />
    <p className="text-sm font-medium">{message}</p>
  </div>
);

export const EmptyState = ({ title, message }: { title: string, message: string }) => (
  <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-border rounded-lg bg-surface/50">
    <h3 className="text-lg font-medium text-white mb-2">{title}</h3>
    <p className="text-sm text-muted max-w-sm">{message}</p>
  </div>
);

export const ErrorState = ({ message }: { message: string }) => (
  <div className="p-4 rounded-lg bg-danger/10 border border-danger/20 text-danger text-sm flex items-center gap-3">
    <span className="font-semibold">Error:</span> {message}
  </div>
);
