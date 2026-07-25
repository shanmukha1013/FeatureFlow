import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Database, Activity, Box, Cpu, FileJson, PlaySquare, Settings, HeartPulse, Shield, GitMerge, PlayCircle } from 'lucide-react';
import { usePlatform } from '../contexts/PlatformContext';

export const Sidebar = () => {
  const NAVIGATION = [
    { name: 'Dashboard', path: '/platform/dashboard', icon: LayoutDashboard },
    { name: 'Digital Twin', path: '/platform/topology', icon: Activity },
    { name: 'Enterprise MLOps', path: '/platform/enterprise', icon: Shield },
    { name: 'Retraining', path: '/platform/retraining', icon: GitMerge },
    { name: 'Experiments', path: '/platform/experiments', icon: Activity },
    { name: 'Inference', path: '/platform/inference', icon: PlayCircle },
    { name: 'Explainability', path: '/platform/explainability', icon: Activity },
    { name: 'Drift Monitor', path: '/platform/drift', icon: Activity },
    { name: 'Models', path: '/platform/models', icon: Box },
    { name: 'Datasets', path: '/platform/datasets', icon: Database },
    { name: 'Features', path: '/platform/features', icon: FileJson },
    { name: 'Pipelines', path: '/platform/pipelines', icon: Cpu },
    { name: 'Monitoring', path: '/platform/monitoring', icon: Activity },
    { name: 'Audit Logs', path: '/platform/audit', icon: Activity },
    { name: 'Health', path: '/platform/health', icon: HeartPulse },
    { name: 'Settings', path: '/platform/settings', icon: Settings }
  ];

  return (
    <div className="w-64 h-screen bg-[#111111] border-r border-border flex flex-col shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <span className="text-lg font-bold text-white tracking-tight">FeatureFlow</span>
      </div>
      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {NAVIGATION.map((link) => (
          <NavLink 
            key={link.path} 
            to={link.path}
            className={({isActive}) => `
              flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors
              ${isActive ? 'bg-[#262626] text-white' : 'text-muted hover:text-white hover:bg-[#1f1f1f]'}
            `}
          >
            <link.icon size={16} />
            {link.name}
          </NavLink>
        ))}
      </nav>
    </div>
  );
};

export const AppLayout = () => {

  return (
    <div className="flex h-screen bg-background overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-background border-b border-border flex items-center px-8 shrink-0 justify-between">
          <div className="flex items-center gap-4">
            <div className="text-sm text-muted">Platform Management</div>
            <div className="flex items-center gap-2 text-xs font-medium text-success bg-success/10 px-2.5 py-1 rounded border border-success/20">
              <div className="w-1.5 h-1.5 rounded-full bg-success"></div>
              Online
            </div>
          </div>
          
          <div className="relative">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
               <div className="text-sm font-medium leading-none">Single-User Mode</div>
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-8 bg-[#0a0a0a]">
          <div className="max-w-6xl mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
