import { usePlatform } from '../contexts/PlatformContext';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { ErrorState } from '../components/States';
import { EventStream } from '../components/EventStream';
import { Zap, Database, Box, TrendingUp } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Dashboard = () => {
  const { stats } = usePlatform();
  const navigate = useNavigate();

  if (!stats) return <ErrorState message="Failed to load platform data." />;

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
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button 
                onClick={() => navigate('/platform/datasets')}
                className="flex items-center justify-between p-4 bg-[#252525] hover:bg-[#2d2d2d] rounded-lg border border-gray-800 transition-colors"
                >
                <div className="flex items-center">
                    <Database className="w-5 h-5 text-blue-400 mr-3" />
                    <span className="text-gray-200 font-medium">Register Dataset</span>
                </div>
                <TrendingUp className="w-4 h-4 text-gray-500" />
                </button>
                <button 
                onClick={() => navigate('/platform/models')}
                className="flex items-center justify-between p-4 bg-[#252525] hover:bg-[#2d2d2d] rounded-lg border border-gray-800 transition-colors"
                >
                <div className="flex items-center">
                    <Box className="w-5 h-5 text-emerald-400 mr-3" />
                    <span className="text-gray-200 font-medium">Deploy Model</span>
                </div>
                <TrendingUp className="w-4 h-4 text-gray-500" />
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
