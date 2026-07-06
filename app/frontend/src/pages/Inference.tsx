import React, { useState } from 'react';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';

export const Inference = () => {
  const [alias, setAlias] = useState('default');
  const [entityId, setEntityId] = useState('entity_123');
  const [features, setFeatures] = useState('{\n  "feature_1": 1.0,\n  "feature_2": 0.5\n}');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<any[]>([]);

  const handlePredict = async () => {
    setLoading(true);
    setError('');
    try {
      const parsedFeatures = JSON.parse(features);
      const res = await apiClient.post('/predict', {
        alias,
        entity_id: entityId,
        features: parsedFeatures
      });
      setResult(res.data);
      setHistory(prev => [res.data, ...prev].slice(0, 5)); // Keep last 5
    } catch (e: any) {
      setError(e.response?.data?.error?.message || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl space-y-6 animate-in fade-in pb-12">
      <PageHeader title="Inference Playground" subtitle="Manually test live predictions against registered model aliases." />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-surface border border-border p-6 rounded-lg space-y-5">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Request Parameters</h2>
          
          <div>
            <label className="block text-xs font-medium text-muted uppercase mb-2">Model Alias</label>
            <input 
              type="text" 
              className="w-full bg-[#0a0a0a] border border-border rounded-md p-2.5 text-sm text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
              value={alias}
              onChange={e => setAlias(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted uppercase mb-2">Entity ID</label>
            <input 
              type="text" 
              className="w-full bg-[#0a0a0a] border border-border rounded-md p-2.5 text-sm text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none transition-all"
              value={entityId}
              onChange={e => setEntityId(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted uppercase mb-2">Feature Vector (JSON)</label>
            <textarea 
              rows={8}
              className="w-full bg-[#0a0a0a] border border-border rounded-md p-2.5 text-sm text-white focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono transition-all"
              value={features}
              onChange={e => setFeatures(e.target.value)}
            />
          </div>

          <button 
            onClick={handlePredict}
            disabled={loading}
            className="w-full bg-white text-black hover:bg-gray-200 font-medium py-2.5 rounded-md transition-colors disabled:opacity-50"
          >
            {loading ? 'Executing Inference...' : 'Run Prediction'}
          </button>
        </div>

        <div className="bg-surface border border-border p-6 rounded-lg space-y-5 flex flex-col">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Prediction Response</h2>
          
          {error && (
            <div className="p-4 bg-danger/10 border border-danger/20 rounded-md text-danger text-sm">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-4 flex-1 flex flex-col">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#0a0a0a] border border-border rounded-md p-4">
                  <div className="text-xs text-muted uppercase tracking-wide">Prediction</div>
                  <div className="text-3xl font-semibold text-white mt-2 tracking-tight">{String(result.prediction)}</div>
                </div>
                <div className="bg-[#0a0a0a] border border-border rounded-md p-4">
                  <div className="text-xs text-muted uppercase tracking-wide">Confidence</div>
                  <div className="text-3xl font-semibold text-white mt-2 tracking-tight">{result.confidence ? (result.confidence * 100).toFixed(1) + '%' : 'N/A'}</div>
                </div>
                <div className="bg-[#0a0a0a] border border-border rounded-md p-4">
                  <div className="text-xs text-muted uppercase tracking-wide">Latency</div>
                  <div className="text-3xl font-semibold text-white mt-2 tracking-tight">{result.latency_ms.toFixed(2)} ms</div>
                </div>
                <div className="bg-[#0a0a0a] border border-border rounded-md p-4">
                  <div className="text-xs text-muted uppercase tracking-wide">Model Version</div>
                  <div className="text-sm font-semibold text-white mt-2 tracking-tight break-all">{result.model_version}</div>
                  <div className="text-xs text-muted mt-1 break-all">{result.model_name}</div>
                </div>
              </div>
              
              <div className="bg-[#0a0a0a] rounded-md p-4 flex-1 overflow-auto border border-border">
                <pre className="text-xs text-muted font-mono whitespace-pre-wrap">
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {!result && !error && !loading && (
            <div className="flex-1 flex items-center justify-center text-muted text-sm border border-dashed border-border rounded-md">
              Execute a prediction to see the response.
            </div>
          )}
        </div>
      </div>

      {history.length > 0 && (
        <div className="bg-surface border border-border rounded-lg p-6 space-y-4 mt-6">
          <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Prediction History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border/50 text-xs uppercase text-muted">
                  <th className="py-3 px-4 font-medium">Timestamp</th>
                  <th className="py-3 px-4 font-medium">Model</th>
                  <th className="py-3 px-4 font-medium">Prediction</th>
                  <th className="py-3 px-4 font-medium">Confidence</th>
                  <th className="py-3 px-4 font-medium text-right">Latency</th>
                </tr>
              </thead>
              <tbody className="text-sm">
                {history.map((h, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-white/5 transition-colors">
                    <td className="py-3 px-4 text-muted">{new Date(h.timestamp).toLocaleTimeString()}</td>
                    <td className="py-3 px-4"><span className="font-mono text-xs">{h.model_name.substring(0, 16)}...</span></td>
                    <td className="py-3 px-4 text-white font-medium">{String(h.prediction)}</td>
                    <td className="py-3 px-4 text-muted">{h.confidence ? (h.confidence * 100).toFixed(1) + '%' : '-'}</td>
                    <td className="py-3 px-4 text-right text-muted">{h.latency_ms.toFixed(2)} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
