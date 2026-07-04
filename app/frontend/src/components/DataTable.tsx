import React from 'react';
import { EmptyState } from './States';

interface Column {
  header: string;
  accessor: string | ((row: any) => React.ReactNode);
  align?: 'left' | 'right' | 'center';
}

export const DataTable = ({ columns, data }: { columns: Column[], data: any[] }) => {
  if (!data || data.length === 0) {
    return <EmptyState title="No records found" message="There is no data to display for this view." />;
  }

  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-muted bg-[#1f1f1f] border-b border-border uppercase">
          <tr>
            {columns.map((col, i) => (
              <th key={i} className={`px-6 py-3 font-medium text-${col.align || 'left'}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-white/[0.02] transition-colors">
              {columns.map((col, j) => (
                <td key={j} className={`px-6 py-4 text-${col.align || 'left'} text-gray-300`}>
                  {typeof col.accessor === 'function' ? col.accessor(row) : row[col.accessor]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
