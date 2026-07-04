import React from 'react';

export const PageHeader = ({ title, subtitle }: { title: string, subtitle?: string }) => (
  <div className="mb-8 border-b border-border pb-4">
    <h1 className="text-3xl font-semibold tracking-tight text-white">{title}</h1>
    {subtitle && <p className="text-muted mt-2 text-sm">{subtitle}</p>}
  </div>
);
