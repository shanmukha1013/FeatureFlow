import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, Database, Activity, Box, Cpu, FileJson, PlaySquare, Settings, HeartPulse } from 'lucide-react';

export const Sidebar = () => {
  const links = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/inference', icon: PlaySquare, label: 'Inference' },
    { to: '/models', icon: Box, label: 'Models' },
    { to: '/datasets', icon: Database, label: 'Datasets' },
    { to: '/features', icon: FileJson, label: 'Features' },
    { to: '/pipelines', icon: Cpu, label: 'Pipelines' },
    { to: '/monitoring', icon: Activity, label: 'Monitoring' },
    { to: '/audit', icon: Activity, label: 'Audit Logs' },
    { to: '/health', icon: HeartPulse, label: 'Health' },
    { to: '/settings', icon: Settings, label: 'Settings' }
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
        <header className="h-16 bg-background border-b border-border flex items-center px-8 shrink-0">
          <div className="flex-1 text-sm text-muted">Platform Management</div>
          <div className="flex items-center gap-2 text-xs font-medium text-success bg-success/10 px-2.5 py-1 rounded border border-success/20">
            <div className="w-1.5 h-1.5 rounded-full bg-success"></div>
            Online
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
