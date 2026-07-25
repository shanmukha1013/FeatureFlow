import React from 'react';
import { usePlatform } from '../contexts/PlatformContext';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { EventStream } from '../components/EventStream';
import { Zap, Database, Box, TrendingUp, Cpu, BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Dashboard = () => {
  const { stats } = usePlatform();
  const navigate = useNavigate();


  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <PageHeader title="Platform Overview" subtitle="Real-time status of the FeatureFlow production environment." />
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="System Health" value={stats?.health} status={stats?.health} />
        <MetricCard title="Total Predictions" value={stats?.total_predictions?.toLocaleString() || 0} />
        <MetricCard title="Avg Latency" value={`${stats?.average_latency?.toFixed(2) || 0} ms`} />
        <MetricCard title="Validation Fails" value={stats?.validation_failures || 0} />
        <MetricCard title="Active Models" value={stats?.registered_models || 0} />
        <MetricCard title="Feature Pipeline Runs" value={stats?.pipeline_count || 0} />
        <MetricCard title="Registered Features" value={stats?.registered_features || 0} />
        <MetricCard title="Registered Datasets" value={stats?.registered_datasets || 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
            <div className="bg-[#1e1e1e] p-6 rounded-lg border border-gray-800">
            <h2 className="text-lg font-semibold text-gray-200 mb-4 flex items-center">
                <Zap className="w-5 h-5 mr-2 text-yellow-400" />
                Quick Actions
            </h2>
            <div className="grid grid-cols-2 gap-3">
                <button onClick={() => navigate('/platform/datasets')} className="flex items-center gap-3 p-4 bg-[#252525] hover:bg-[#2d2d2d] rounded-lg border border-gray-800 transition-colors">
                  <Database className="w-5 h-5 text-blue-400" />
                  <span className="text-gray-200 font-medium text-sm">Upload Dataset</span>
                </button>
                <button onClick={() => navigate('/platform/training')} className="flex items-center gap-3 p-4 bg-[#252525] hover:bg-[#2d2d2d] rounded-lg border border-gray-800 transition-colors">
                  <Cpu className="w-5 h-5 text-purple-400" />
                  <span className="text-gray-200 font-medium text-sm">Train Model</span>
                </button>
                <button onClick={() => navigate('/platform/inference')} className="flex items-center gap-3 p-4 bg-[#252525] hover:bg-[#2d2d2d] rounded-lg border border-gray-800 transition-colors">
                  <Box className="w-5 h-5 text-emerald-400" />
                  <span className="text-gray-200 font-medium text-sm">Run Inference</span>
                </button>
                <button onClick={() => navigate('/platform/monitoring')} className="flex items-center gap-3 p-4 bg-[#252525] hover:bg-[#2d2d2d] rounded-lg border border-gray-800 transition-colors">
                  <BarChart3 className="w-5 h-5 text-orange-400" />
                  <span className="text-gray-200 font-medium text-sm">View Metrics</span>
                </button>
            </div>
            </div>
        </div>

        <div className="lg:col-span-1 h-[400px]">
            <EventStream />
        </div>
      </div>

      <div className="bg-[#1e1e1e] rounded-lg p-6 border border-gray-800 mt-6">
        <h2 className="text-lg font-semibold text-gray-200 mb-4 flex items-center">
          <Database className="w-5 h-5 mr-2 text-indigo-400" />
          Active Subsystems
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-[#151515] border border-gray-800 rounded flex flex-col items-center justify-center">
                <span className="text-gray-400 text-xs font-mono mb-2">REDIS BUS</span>
                <span className="text-emerald-400 font-semibold text-sm">CONNECTED</span>
            </div>
            <div className="p-4 bg-[#151515] border border-gray-800 rounded flex flex-col items-center justify-center">
                <span className="text-gray-400 text-xs font-mono mb-2">WEBSOCKETS</span>
                <span className="text-emerald-400 font-semibold text-sm">ACTIVE</span>
            </div>
            <div className="p-4 bg-[#151515] border border-gray-800 rounded flex flex-col items-center justify-center">
                <span className="text-gray-400 text-xs font-mono mb-2">FEATURE STORE</span>
                <span className="text-emerald-400 font-semibold text-sm">SYNCED</span>
            </div>
            <div className="p-4 bg-[#151515] border border-gray-800 rounded flex flex-col items-center justify-center">
                <span className="text-gray-400 text-xs font-mono mb-2">MODEL REGISTRY</span>
                <span className="text-emerald-400 font-semibold text-sm">ONLINE</span>
            </div>
        </div>
      </div>
    </div>
  );
};
