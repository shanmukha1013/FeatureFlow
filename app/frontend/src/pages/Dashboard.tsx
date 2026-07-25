import { usePlatform } from '../contexts/PlatformContext';
import { MetricCard } from '../components/MetricCard';
import { PageHeader } from '../components/PageHeader';
import { ErrorState } from '../components/States';

export const Dashboard = () => {
  const { stats } = usePlatform();

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

      <div className="bg-surface rounded-lg p-8 border border-border h-64 flex items-center justify-center">
        <p className="text-muted text-sm">Detailed telemetry charts will render here (Recharts placeholder).</p>
      </div>
    </div>
  );
};
