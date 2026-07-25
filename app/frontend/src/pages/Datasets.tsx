import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { StatusBadge } from '../components/StatusBadge';
import { LoadingSpinner } from '../components/States';
import { Upload, Database, X, CheckCircle, AlertTriangle, Plus, FileText } from 'lucide-react';

const formatBytes = (bytes: number) => {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const UploadModal = ({ onClose, onSuccess }: { onClose: () => void; onSuccess: () => void }) => {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) setFile(dropped);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    if (name) formData.append('name', name);
    if (description) formData.append('description', description);
    formData.append('auto_train', 'true');
    try {
      const res = await apiClient.post('/management/datasets/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(res.data);
      onSuccess();
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl w-full max-w-lg p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Upload className="w-5 h-5 text-indigo-400" />
            Upload Dataset
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        {result ? (
          <div className="space-y-4">
            <div className="flex items-center gap-3 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
              <CheckCircle className="w-6 h-6 text-emerald-400" />
              <div>
                <p className="font-semibold text-emerald-400">Upload Successful</p>
                <p className="text-sm text-gray-400">{result.row_count?.toLocaleString()} rows, {result.column_count} columns, {result.new_features_registered?.length} features registered</p>
              </div>
            </div>
            {result.training_triggered && (
              <p className="text-sm text-indigo-400 text-center">🚀 Training pipeline is running in the background...</p>
            )}
            <button onClick={onClose} className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium">Done</button>
          </div>
        ) : (
          <div className="space-y-4">
            <div
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragging ? 'border-indigo-500 bg-indigo-500/10' : 'border-gray-700 hover:border-gray-500'
              }`}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input ref={fileInputRef} type="file" accept=".csv,.parquet" hidden onChange={(e) => setFile(e.target.files?.[0] || null)} />
              {file ? (
                <div className="flex items-center justify-center gap-2 text-white">
                  <FileText className="w-5 h-5 text-indigo-400" />
                  <span className="font-medium">{file.name}</span>
                  <span className="text-gray-500 text-sm">({formatBytes(file.size)})</span>
                </div>
              ) : (
                <div>
                  <Upload className="w-8 h-8 text-gray-500 mx-auto mb-2" />
                  <p className="text-gray-400 text-sm">Drop a CSV or Parquet file here, or click to browse</p>
                </div>
              )}
            </div>

            <input
              type="text"
              placeholder="Dataset name (optional, auto-inferred from filename)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-[#111] border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:border-indigo-500 outline-none"
            />
            <textarea
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
              className="w-full bg-[#111] border border-gray-800 rounded-lg px-4 py-2.5 text-sm text-white placeholder-gray-600 focus:border-indigo-500 outline-none resize-none"
            />

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                <AlertTriangle className="w-4 h-4" />
                {error}
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={onClose} className="flex-1 py-2.5 border border-gray-700 text-gray-300 rounded-lg hover:bg-gray-800">Cancel</button>
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {uploading ? <><div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />Uploading...</> : <><Upload className="w-4 h-4" />Upload & Train</>}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export const Datasets = () => {
  const queryClient = useQueryClient();
  const [showUpload, setShowUpload] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => apiClient.get('/management/datasets').then(res => res.data),
    refetchInterval: 5000,
  });

  const datasets = data?.items || [];

  if (isLoading) return <LoadingSpinner message="Loading datasets..." />;

  return (
    <div className="space-y-6 animate-in fade-in">
      <div className="flex items-center justify-between">
        <PageHeader title="Dataset Registry" subtitle="Upload, validate, and manage raw data sources." />
        <button
          onClick={() => setShowUpload(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium text-sm transition-colors"
        >
          <Plus className="w-4 h-4" />
          Upload Dataset
        </button>
      </div>

      {datasets.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 space-y-6 border-2 border-dashed border-gray-800 rounded-xl">
          <div className="w-16 h-16 bg-indigo-500/10 rounded-full flex items-center justify-center">
            <Database className="w-8 h-8 text-indigo-400" />
          </div>
          <div className="text-center">
            <h3 className="text-xl font-bold text-white mb-2">Welcome to FeatureFlow</h3>
            <p className="text-gray-400 max-w-md">Upload your first dataset to begin the ML lifecycle. FeatureFlow will automatically profile it, register features, train models, and start monitoring.</p>
          </div>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium"
          >
            <Upload className="w-5 h-5" />
            Upload Your First Dataset
          </button>
        </div>
      ) : (
        <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800 bg-[#111]">
                {['Dataset Name', 'Rows', 'Columns', 'Features', 'Version', 'Memory', 'Status', 'Created'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {datasets.map((d: any) => (
                <tr
                  key={d.id}
                  className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition-colors"
                  onClick={() => setSelectedDataset(selectedDataset?.id === d.id ? null : d)}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <Database className="w-4 h-4 text-indigo-400" />
                      <span className="font-medium text-white">{d.dataset_name || d.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-sm">{(d.row_count || 0).toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-400 text-sm">{d.column_count || 0}</td>
                  <td className="px-4 py-3 text-gray-400 text-sm">{d.feature_count || 0}</td>
                  <td className="px-4 py-3 text-gray-400 text-sm">v{d.version || 1}</td>
                  <td className="px-4 py-3 text-gray-400 text-sm">{formatBytes(d.estimated_memory_bytes || 0)}</td>
                  <td className="px-4 py-3"><StatusBadge status={d.status || 'ACTIVE'} /></td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{d.created_at ? new Date(d.created_at).toLocaleDateString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {selectedDataset && (
            <div className="border-t border-gray-800 p-4 bg-[#111] space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-white">{selectedDataset.dataset_name || selectedDataset.name} — Details</h4>
                <button onClick={() => setSelectedDataset(null)} className="text-gray-500 hover:text-white"><X className="w-4 h-4" /></button>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-500">Null % Max:</span> <span className="text-white">{selectedDataset.null_percentage_max?.toFixed(1) || 0}%</span></div>
                <div><span className="text-gray-500">Duplicates:</span> <span className="text-white">{selectedDataset.duplicate_count || 0}</span></div>
                <div><span className="text-gray-500">Profiling:</span> <span className="text-white">{selectedDataset.profiling_status || 'PENDING'}</span></div>
              </div>
              {selectedDataset.columns && selectedDataset.columns.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Columns</p>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedDataset.columns.map((col: string) => (
                      <span key={col} className="px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded font-mono">
                        {col}
                        {selectedDataset.inferred_dtypes?.[col] && <span className="text-gray-500 ml-1">({selectedDataset.inferred_dtypes[col]})</span>}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['datasets'] });
          }}
        />
      )}
    </div>
  );
};
