import React from 'react';
import { PageHeader } from '../components/PageHeader';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export const Monitoring = () => {
  // Simplified placeholder charts for UI demonstration without complex backend mapping
  const mockLatency = [
    { time: '10:00', ms: 45 }, { time: '10:05', ms: 52 }, 
    { time: '10:10', ms: 48 }, { time: '10:15', ms: 61 },
    { time: '10:20', ms: 43 }, { time: '10:25', ms: 38 }
  ];

  return (
    <div className="space-y-6 animate-in fade-in">
      <PageHeader title="Monitoring Metrics" subtitle="Visualizing real-time telemetry from the backend." />
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface border border-border p-6 rounded-lg">
          <h3 className="text-sm font-medium text-muted mb-4 uppercase">Prediction Latency (ms)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={mockLatency}>
                <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
                <XAxis dataKey="time" stroke="#a1a1aa" fontSize={12} />
                <YAxis stroke="#a1a1aa" fontSize={12} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#171717', borderColor: '#262626' }}
                  itemStyle={{ color: '#0070f3' }}
                />
                <Bar dataKey="ms" fill="#0070f3" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-surface border border-border p-6 rounded-lg flex items-center justify-center h-[340px]">
          <p className="text-muted text-sm text-center">
            Additional charts (e.g. Error Rates, Throughput) require timeseries persistence.<br/><br/>
            Currently, the Management API exposes single-value counters.<br/>
            Timeseries integration planned for next phase.
          </p>
        </div>
      </div>
    </div>
  );
};
