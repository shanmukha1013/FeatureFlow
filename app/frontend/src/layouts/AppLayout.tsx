import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { 
  LayoutDashboard, Database, Activity, Box, Cpu, FileJson, 
  Settings, HeartPulse, Shield, GitMerge, PlayCircle, 
  Network, FlaskConical, Eye, TrendingDown, ClipboardList,
  GitBranch, BarChart3
} from 'lucide-react';

const NAVIGATION = [
  // Orchestration
  { section: 'Orchestration', items: [
    { name: 'Lifecycle Canvas', path: '/platform/canvas', icon: LayoutDashboard },
  ]},
  // Data & Features
  { section: 'Data & Features', items: [
    { name: 'Datasets', path: '/platform/datasets', icon: Database },
    { name: 'Features', path: '/platform/features', icon: FileJson },
    { name: 'Pipelines', path: '/platform/pipelines', icon: GitBranch },
  ]},
  // Models & Serving
  { section: 'Models & Serving', items: [
    { name: 'Training', path: '/platform/training', icon: Cpu },
    { name: 'Models', path: '/platform/models', icon: Box },
    { name: 'Retraining', path: '/platform/retraining', icon: GitMerge },
    { name: 'Inference', path: '/platform/inference', icon: PlayCircle },
  ]},
  // Observability
  { section: 'Observability', items: [
    { name: 'Drift Monitor', path: '/platform/drift', icon: TrendingDown },
    { name: 'Monitoring', path: '/platform/monitoring', icon: BarChart3 },
    { name: 'Explainability', path: '/platform/explainability', icon: Eye },
  ]},
  // Enterprise
  { section: 'Enterprise', items: [
    { name: 'Audit Logs', path: '/platform/audit', icon: ClipboardList },
    { name: 'Enterprise MLOps', path: '/platform/enterprise', icon: Shield },
    { name: 'Settings', path: '/platform/settings', icon: Settings },
  ]},
];

export const Sidebar = () => {
  return (
    <div className="w-60 h-screen bg-[#0d0d0d] border-r border-[#1f1f1f] flex flex-col shrink-0">
      <div className="h-14 flex items-center px-5 border-b border-[#1f1f1f]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-indigo-600 flex items-center justify-center">
            <Activity size={12} className="text-white" />
          </div>
          <span className="text-sm font-bold text-white tracking-tight">FeatureFlow</span>
        </div>
      </div>
      <nav className="flex-1 py-4 overflow-y-auto scrollbar-none">
        {NAVIGATION.map((section) => (
          <div key={section.section} className="mb-4">
            <p className="px-4 mb-1 text-[10px] font-semibold text-gray-600 uppercase tracking-widest">{section.section}</p>
            {section.items.map((link) => (
              <NavLink
                key={link.path}
                to={link.path}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-4 py-2 text-sm transition-colors ${
                    isActive
                      ? 'text-white bg-[#1a1a1a] border-r-2 border-indigo-500'
                      : 'text-gray-500 hover:text-gray-200 hover:bg-[#161616]'
                  }`
                }
              >
                <link.icon size={14} />
                {link.name}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
    </div>
  );
};

export const AppLayout = () => {
  return (
    <div className="flex h-screen bg-[#0a0a0a] overflow-hidden font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-[#0d0d0d] border-b border-[#1f1f1f] flex items-center px-8 shrink-0 justify-between">
          <div className="flex items-center gap-4">
            <div className="text-xs text-gray-500">FeatureFlow MLOps Platform</div>
            <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-400">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Online
            </div>
          </div>
          <div className="text-[10px] text-gray-700 font-mono">v1.0.0</div>
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
