import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Database, Activity, Box, Cpu, FileJson, PlaySquare, Settings, HeartPulse, Shield } from 'lucide-react';
import { usePlatform } from '../contexts/PlatformContext';

export const Sidebar = () => {
  const links = [
    { to: '/platform/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/platform/enterprise', icon: Shield, label: 'Enterprise MLOps' },
    { to: '/platform/retraining', icon: Activity, label: 'Retraining' },
    { to: '/platform/experiments', icon: Activity, label: 'Experiments' },
    { to: '/platform/inference', icon: PlaySquare, label: 'Inference' },
    { to: '/platform/explainability', icon: Activity, label: 'Explainability' },
    { to: '/platform/drift', icon: Activity, label: 'Drift Monitor' },
    { to: '/platform/models', icon: Box, label: 'Models' },
    { to: '/platform/datasets', icon: Database, label: 'Datasets' },
    { to: '/platform/features', icon: FileJson, label: 'Features' },
    { to: '/platform/pipelines', icon: Cpu, label: 'Pipelines' },
    { to: '/platform/monitoring', icon: Activity, label: 'Monitoring' },
    { to: '/platform/audit', icon: Activity, label: 'Audit Logs' },
    { to: '/platform/health', icon: HeartPulse, label: 'Health' },
    { to: '/platform/settings', icon: Settings, label: 'Settings' }
  ];

  return (
    <div className="w-64 h-screen bg-[#111111] border-r border-border flex flex-col shrink-0">
      <div className="h-16 flex items-center px-6 border-b border-border">
        <span className="text-lg font-bold text-white tracking-tight">FeatureFlow</span>
      </div>
      <nav className="flex-1 py-4 px-3 space-y-0.5 overflow-y-auto">
        {links.map((link) => (
          <NavLink 
            key={link.to} 
            to={link.to}
            className={({isActive}) => `
              flex items-center gap-3 px-3 py-2 rounded-md font-medium text-sm transition-colors
              ${isActive ? 'bg-[#262626] text-white' : 'text-muted hover:text-white hover:bg-[#1f1f1f]'}
            `}
          >
            <link.icon size={16} />
            {link.label}
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
