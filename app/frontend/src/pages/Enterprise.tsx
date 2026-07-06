import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { PageHeader } from '../components/PageHeader';
import { LoadingSpinner } from '../components/States';
import { Shield, Database, Zap, Activity, Users, Split } from 'lucide-react';

export const Enterprise = () => {
  const [activeTab, setActiveTab] = useState<'deployments' | 'featurestore' | 'security'>('deployments');

  const { data: champion } = useQuery({ queryKey: ['champion'], queryFn: () => apiClient.get('/management/champion').then(res => res.data).catch(() => null) });
  const { data: challengers } = useQuery({ queryKey: ['challengers'], queryFn: () => apiClient.get('/management/challengers').then(res => res.data.items).catch(() => []) });
  const { data: cacheStats } = useQuery({ queryKey: ['cache'], queryFn: () => apiClient.get('/management/cache').then(res => res.data).catch(() => null) });
  const { data: users } = useQuery({ queryKey: ['users'], queryFn: () => apiClient.get('/management/users').then(res => res.data.items).catch(() => []) });

  return (
    <div className="space-y-6 animate-in fade-in pb-12 max-w-6xl">
      <PageHeader title="Enterprise MLOps" subtitle="Centralized command center for Champion/Challenger deployments, Feature Stores, and Security." />

      <div className="flex border-b border-border mb-6 space-x-6">
        <button onClick={() => setActiveTab('deployments')} className={`pb-3 text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'deployments' ? 'text-primary border-b-2 border-primary' : 'text-muted hover:text-white'}`}><Split size={16} /> Deployments & Routing</button>
        <button onClick={() => setActiveTab('featurestore')} className={`pb-3 text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'featurestore' ? 'text-primary border-b-2 border-primary' : 'text-muted hover:text-white'}`}><Database size={16} /> Feature Stores</button>
        <button onClick={() => setActiveTab('security')} className={`pb-3 text-sm font-medium transition-colors flex items-center gap-2 ${activeTab === 'security' ? 'text-primary border-b-2 border-primary' : 'text-muted hover:text-white'}`}><Shield size={16} /> Security & RBAC</button>
      </div>

      {activeTab === 'deployments' && (
        <div className="space-y-6">
          <div className="bg-surface border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2"><Activity size={16}/> Active Champion</h2>
            {champion ? (
              <div className="p-4 bg-success/10 border border-success/30 rounded-md">
                <div className="font-mono text-success text-lg">{champion.model_id}</div>
                <div className="text-sm text-muted mt-1">Algorithm: {champion.algorithm} | Accuracy: {(champion.metrics.accuracy * 100).toFixed(2)}%</div>
                <div className="text-xs text-muted mt-2">Receiving 100% of default traffic via routing engine.</div>
              </div>
            ) : <div className="text-sm text-muted">No champion model actively deployed.</div>}
          </div>

          <div className="bg-surface border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2"><Split size={16}/> Active Challengers</h2>
            {challengers && challengers.length > 0 ? challengers.map((c: any) => (
              <div key={c.model_id} className="p-4 bg-[#0a0a0a] border border-border rounded-md flex justify-between items-center">
                <div>
                  <div className="font-mono text-white text-sm">{c.model_id}</div>
                  <div className="text-xs text-muted mt-1">Algorithm: {c.algorithm} | Accuracy: {(c.metrics?.accuracy * 100).toFixed(2)}%</div>
                </div>
                <button className="bg-primary/10 text-primary px-4 py-1.5 rounded text-xs font-medium border border-primary/20">Promote to Champion</button>
              </div>
            )) : <div className="text-sm text-muted">No challengers currently deployed for A/B testing.</div>}
          </div>
        </div>
      )}

      {activeTab === 'featurestore' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-surface border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2"><Database size={16}/> PostgreSQL Offline Store</h2>
            <div className="p-4 bg-[#0a0a0a] border border-border rounded-md space-y-2">
              <div className="flex justify-between"><span className="text-muted text-sm">Status</span><span className="text-success font-mono text-sm">CONNECTED</span></div>
              <div className="flex justify-between"><span className="text-muted text-sm">Mode</span><span className="text-white font-mono text-sm">Point-in-Time Correct</span></div>
              <div className="flex justify-between"><span className="text-muted text-sm">Driver</span><span className="text-white font-mono text-sm">asyncpg (Simulated)</span></div>
            </div>
          </div>
          
          <div className="bg-surface border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2"><Zap size={16}/> Redis Online Cache</h2>
            {cacheStats ? (
              <div className="p-4 bg-[#0a0a0a] border border-border rounded-md space-y-2">
                <div className="flex justify-between"><span className="text-muted text-sm">Status</span><span className="text-success font-mono text-sm">CONNECTED</span></div>
                <div className="flex justify-between"><span className="text-muted text-sm">Cache Hits</span><span className="text-white font-mono text-sm">{cacheStats.hits}</span></div>
                <div className="flex justify-between"><span className="text-muted text-sm">Cache Misses</span><span className="text-white font-mono text-sm">{cacheStats.misses}</span></div>
                <div className="flex justify-between"><span className="text-muted text-sm">Memory Usage</span><span className="text-white font-mono text-sm">{(cacheStats.size_bytes / 1024).toFixed(2)} KB</span></div>
              </div>
            ) : <LoadingSpinner message="Loading cache stats..." />}
          </div>
        </div>
      )}

      {activeTab === 'security' && (
        <div className="space-y-6">
          <div className="bg-surface border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2"><Shield size={16}/> JWT Authentication</h2>
            <div className="text-sm text-muted p-4 border border-border bg-[#0a0a0a] rounded-md">
              All management API routes are strictly protected via Bearer Tokens and Role-Based Access Control (RBAC). 
              Currently running in Demo Bypass mode for UI rendering.
            </div>
          </div>

          <div className="bg-surface border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2"><Users size={16}/> Registered Users</h2>
            <div className="space-y-2">
              {users?.map((u: any, i: number) => (
                <div key={i} className="p-3 bg-[#0a0a0a] border border-border rounded-md flex justify-between items-center">
                  <span className="text-sm text-white font-medium">{u.username}</span>
                  <span className="text-xs font-mono bg-white/5 px-2 py-1 rounded text-muted">{u.role}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
