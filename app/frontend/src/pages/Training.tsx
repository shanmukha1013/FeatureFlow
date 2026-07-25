import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { LoadingSpinner } from '../components/States';
import { StatusBadge } from '../components/StatusBadge';
import { Cpu, Play, ChevronDown, CheckCircle, XCircle, AlertCircle, Database, Zap } from 'lucide-react';

const ALGORITHMS = [
  { id: 'auto', label: 'Auto-select Best (Recommended)', description: 'Trains all algorithms and promotes the winner' },
  { id: 'LogisticRegression', label: 'Logistic Regression', description: 'Fast linear classifier, great for binary classification' },
  { id: 'DecisionTree', label: 'Decision Tree', description: 'Interpretable tree-based classifier' },
  { id: 'RandomForest', label: 'Random Forest', description: 'Ensemble of trees, robust and accurate' },
];

const TrainingJobCard = ({ job }: { job: any }) => {
  const isRunning = job.status?.toLowerCase().includes('started') || job.status?.toLowerCase().includes('running');
  const isComplete = job.status?.toLowerCase().includes('completed');
  const isFailed = job.status?.toLowerCase().includes('failed');

  return (
    <div className={`p-4 rounded-xl border transition-all ${
      isFailed ? 'border-red-500/30 bg-red-500/5' :
      isComplete ? 'border-emerald-500/30 bg-emerald-500/5' :
      isRunning ? 'border-indigo-500/30 bg-indigo-500/5' :
      'border-gray-800 bg-[#1a1a1a]'
    }`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isRunning && <div className="w-3 h-3 rounded-full bg-indigo-500 animate-pulse" />}
          {isComplete && <CheckCircle className="w-4 h-4 text-emerald-400" />}
          {isFailed && <XCircle className="w-4 h-4 text-red-400" />}
          <span className="font-semibold text-white text-sm">{job.dataset_name || 'Unknown Dataset'}</span>
        </div>
        <span className="text-xs text-gray-500">{job.timestamp ? new Date(job.timestamp).toLocaleString() : '-'}</span>
      </div>
      <p className="text-xs text-gray-500">{job.status?.replace(/_/g, ' ')}</p>
      {job.details?.error && <p className="text-xs text-red-400 mt-1">{job.details.error}</p>}
    </div>
  );
};

export const Training = () => {
  const queryClient = useQueryClient();
  const [selectedDataset, setSelectedDataset] = useState('');
  const [selectedAlgorithm, setSelectedAlgorithm] = useState('auto');
  const [targetColumn, setTargetColumn] = useState('');
  const [trainingResult, setTrainingResult] = useState<any>(null);

  const { data: datasetsData, isLoading: datasetsLoading } = useQuery({
    queryKey: ['datasets_training'],
    queryFn: () => apiClient.get('/management/datasets').then(res => res.data),
  });

  const { data: jobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['retraining_jobs_training'],
    queryFn: () => apiClient.get('/management/retraining').then(res => res.data),
    refetchInterval: 3000,
  });

  const datasets = datasetsData?.items || [];
  const selectedDatasetObj = datasets.find((d: any) => d.name === selectedDataset || d.dataset_name === selectedDataset);
  const availableColumns = selectedDatasetObj?.columns || Object.keys(selectedDatasetObj?.inferred_dtypes || {});

  const trainMutation = useMutation({
    mutationFn: (payload: { dataset_name: string; trigger_type: string }) =>
      apiClient.post('/management/retraining/start', payload),
    onSuccess: (data) => {
      setTrainingResult({ status: 'started', message: 'Training pipeline started in background. All algorithms will be evaluated and the best will be promoted to champion.' });
      queryClient.invalidateQueries({ queryKey: ['retraining_jobs_training'] });
      queryClient.invalidateQueries({ queryKey: ['experiments'] });
      queryClient.invalidateQueries({ queryKey: ['models'] });
    },
    onError: (e: any) => {
      setTrainingResult({ status: 'error', message: e.response?.data?.detail || 'Training failed to start.' });
    }
  });

  const handleTrain = () => {
    if (!selectedDataset) return;
    setTrainingResult(null);
    trainMutation.mutate({ dataset_name: selectedDataset, trigger_type: 'MANUAL' });
  };

  const recentJobs = jobs?.items || [];

  return (
    <div className="space-y-8 animate-in fade-in">
      <PageHeader title="Model Training" subtitle="Select a dataset, configure your algorithm, and launch training. The best model is automatically promoted." />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Training Configuration */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-6 space-y-5">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
              <Database className="w-4 h-4 text-blue-400" />
              1. Select Dataset
            </h2>

            {datasetsLoading ? (
              <LoadingSpinner message="Loading datasets..." />
            ) : datasets.length === 0 ? (
              <div className="p-4 border border-dashed border-gray-700 rounded-lg text-center">
                <p className="text-gray-500 text-sm">No datasets found. Upload a dataset first.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {datasets.map((d: any) => {
                  const name = d.name || d.dataset_name;
                  const isSelected = selectedDataset === name;
                  return (
                    <div
                      key={d.id}
                      onClick={() => { setSelectedDataset(name); setTargetColumn(''); }}
                      className={`p-4 rounded-lg border cursor-pointer transition-all ${
                        isSelected ? 'border-indigo-500 bg-indigo-500/10' : 'border-gray-800 hover:border-gray-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Database className={`w-4 h-4 ${isSelected ? 'text-indigo-400' : 'text-gray-500'}`} />
                          <div>
                            <p className="font-medium text-white">{name}</p>
                            <p className="text-xs text-gray-500">{(d.row_count || 0).toLocaleString()} rows · {d.column_count || 0} columns · {d.feature_count || 0} features</p>
                          </div>
                        </div>
                        {isSelected && <CheckCircle className="w-4 h-4 text-indigo-400" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {selectedDataset && (
            <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-6 space-y-5">
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                2. Select Algorithm
              </h2>
              <div className="space-y-2">
                {ALGORITHMS.map((algo) => (
                  <div
                    key={algo.id}
                    onClick={() => setSelectedAlgorithm(algo.id)}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      selectedAlgorithm === algo.id ? 'border-indigo-500 bg-indigo-500/10' : 'border-gray-800 hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-white">{algo.label}</p>
                        <p className="text-xs text-gray-500">{algo.description}</p>
                      </div>
                      {selectedAlgorithm === algo.id && <CheckCircle className="w-4 h-4 text-indigo-400" />}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedDataset && availableColumns.length > 0 && (
            <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-6 space-y-4">
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
                <Zap className="w-4 h-4 text-yellow-400" />
                3. Target Column (Optional)
              </h2>
              <p className="text-xs text-gray-500">Leave blank for automatic target selection.</p>
              <select
                value={targetColumn}
                onChange={(e) => setTargetColumn(e.target.value)}
                className="w-full bg-[#111] border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-white focus:border-indigo-500 outline-none"
              >
                <option value="">-- Auto-detect target column --</option>
                {availableColumns.map((col: string) => (
                  <option key={col} value={col}>{col}</option>
                ))}
              </select>
            </div>
          )}

          {/* Train Button */}
          <button
            onClick={handleTrain}
            disabled={!selectedDataset || trainMutation.isPending}
            className="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-semibold text-lg disabled:opacity-50 flex items-center justify-center gap-3 transition-all shadow-lg shadow-indigo-500/20"
          >
            {trainMutation.isPending ? (
              <><div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />Launching Pipeline...</>
            ) : (
              <><Play className="w-5 h-5" />Launch Training Pipeline</>
            )}
          </button>

          {trainingResult && (
            <div className={`p-4 rounded-xl border flex items-start gap-3 ${
              trainingResult.status === 'error' ? 'border-red-500/30 bg-red-500/5' : 'border-emerald-500/30 bg-emerald-500/5'
            }`}>
              {trainingResult.status === 'error'
                ? <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                : <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
              }
              <p className={`text-sm ${trainingResult.status === 'error' ? 'text-red-300' : 'text-emerald-300'}`}>
                {trainingResult.message}
              </p>
            </div>
          )}
        </div>

        {/* Recent Jobs Sidebar */}
        <div className="space-y-4">
          <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              Recent Jobs
            </h3>
            {jobsLoading ? (
              <LoadingSpinner message="Loading..." />
            ) : recentJobs.length === 0 ? (
              <p className="text-gray-600 text-sm text-center py-4">No training jobs yet.</p>
            ) : (
              <div className="space-y-3">
                {recentJobs.slice(0, 10).map((job: any, i: number) => (
                  <TrainingJobCard key={i} job={job} />
                ))}
              </div>
            )}
          </div>

          <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">How It Works</h3>
            <div className="space-y-2.5 text-xs text-gray-500">
              {[
                'Upload a dataset with valid columns',
                'Select target column (auto-detected if blank)',
                'Launch pipeline — 3 algorithms train in parallel',
                'Best model is automatically promoted to Champion',
                'Experiment records created for each run',
                'Artifacts saved locally for inference',
              ].map((step, i) => (
                <div key={i} className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-gray-800 text-gray-500 text-xs flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                  <span>{step}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
