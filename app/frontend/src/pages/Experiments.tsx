import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner, ErrorState } from '../components/States';
import { FlaskConical, Trophy, BarChart2 } from 'lucide-react';

export const Experiments = () => {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<any>(null);
  const [comparingLoading, setComparingLoading] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ['experiments'],
    queryFn: () => apiClient.get('/management/experiments?size=100').then(res => res.data),
    refetchInterval: 10000,
  });

  const handleCompare = async () => {
    if (selectedIds.length < 2) return;
    setComparingLoading(true);
    try {
      const res = await apiClient.get(`/management/experiments/compare?ids=${selectedIds.join(',')}`);
      setComparison(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setComparingLoading(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  if (isLoading) return <LoadingSpinner message="Loading experiments..." />;
  if (error) return <ErrorState message="Could not fetch experiments." />;

  const experiments = data?.items || [];

  return (
    <div className="space-y-6 animate-in fade-in pb-12">
      <div className="flex justify-between items-start">
        <PageHeader title="Experiment Tracking" subtitle="Every training run is automatically tracked as an experiment." />
        <button
          onClick={handleCompare}
          disabled={selectedIds.length < 2 || comparingLoading}
          className="bg-indigo-600 text-white px-4 py-2 rounded-md font-medium text-sm disabled:opacity-50 transition-opacity flex items-center gap-2"
        >
          <BarChart2 className="w-4 h-4" />
          Compare ({selectedIds.length})
        </button>
      </div>

      {experiments.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 border-2 border-dashed border-gray-800 rounded-xl space-y-4">
          <FlaskConical className="w-12 h-12 text-gray-700" />
          <div className="text-center">
            <h3 className="text-lg font-semibold text-gray-400 mb-2">No Experiments Yet</h3>
            <p className="text-gray-600 text-sm max-w-sm">Upload a dataset and training will automatically create experiments. Each algorithm (Logistic Regression, Random Forest, Decision Tree) creates a separate tracked experiment.</p>
          </div>
        </div>
      ) : (
        <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 bg-[#111]">
                <th className="px-4 py-3 w-10"></th>
                {['Experiment', 'Algorithm', 'Dataset', 'Accuracy', 'F1', 'Status', 'Started'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {experiments.map((exp: any) => {
                const isSelected = selectedIds.includes(exp.id);
                const accuracy = exp.metrics?.accuracy;
                const f1 = exp.metrics?.f1 || exp.metrics?.f1_score || exp.metrics?.f1_weighted;
                return (
                  <tr key={exp.id} className={`border-b border-gray-800/50 transition-colors ${isSelected ? 'bg-indigo-900/20' : 'hover:bg-gray-800/30'}`}>
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(exp.id)}
                        className="rounded border-gray-700 bg-[#0a0a0a] text-indigo-600 focus:ring-indigo-500"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-gray-400">{exp.id?.substring(0, 12)}...</span>
                      <p className="text-sm text-white font-medium">{exp.name || 'Unnamed'}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-1 bg-gray-800 text-gray-300 text-xs rounded font-mono">{exp.algorithm || '-'}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">{exp.dataset || '-'}</td>
                    <td className="px-4 py-3">
                      {accuracy != null ? (
                        <span className={`font-semibold ${accuracy >= 0.8 ? 'text-emerald-400' : accuracy >= 0.6 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {(accuracy * 100).toFixed(1)}%
                        </span>
                      ) : <span className="text-gray-600">-</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {f1 != null ? `${(f1 * 100).toFixed(1)}%` : '-'}
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={exp.status || 'RUNNING'} /></td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {exp.start_time ? new Date(exp.start_time).toLocaleString() : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {comparison && Object.keys(comparison).length > 0 && (
        <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-6 space-y-4 mt-6">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-indigo-400" />
            Experiment Comparison
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(comparison).map(([expId, exp]: [string, any]) => {
              const bestAcc = Math.max(...Object.values(comparison).map((e: any) => e.metrics?.accuracy || 0));
              const isBest = (exp.metrics?.accuracy || 0) === bestAcc;
              return (
                <div key={expId} className={`p-4 rounded-xl border ${isBest ? 'border-yellow-500/50 bg-yellow-500/5' : 'border-gray-800 bg-[#111]'}`}>
                  <div className="flex justify-between items-start mb-4">
                    <div className="font-mono text-xs text-gray-500">{expId.substring(0, 12)}...</div>
                    {isBest && (
                      <span className="flex items-center gap-1 text-xs font-bold text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded-full">
                        <Trophy className="w-3 h-3" /> BEST
                      </span>
                    )}
                  </div>
                  <div className="space-y-3 text-sm">
                    <div><p className="text-xs text-gray-600 uppercase">Algorithm</p><p className="font-medium text-white">{exp.algorithm || '-'}</p></div>
                    <div><p className="text-xs text-gray-600 uppercase">Accuracy</p><p className="text-2xl font-bold text-indigo-400">{exp.metrics?.accuracy ? `${(exp.metrics.accuracy * 100).toFixed(2)}%` : '-'}</p></div>
                    <div><p className="text-xs text-gray-600 uppercase">F1 Score</p><p className="text-lg font-semibold">{exp.metrics?.f1 ? `${(exp.metrics.f1 * 100).toFixed(2)}%` : '-'}</p></div>
                    {exp.hyperparameters && <div><p className="text-xs text-gray-600 uppercase">Hyperparameters</p><p className="text-xs font-mono text-gray-400">{JSON.stringify(exp.hyperparameters)}</p></div>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
