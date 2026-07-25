import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, Shield, Cpu } from 'lucide-react';

export const Landing = () => {
  return (
    <div className="min-h-screen bg-neutral-950 text-white overflow-hidden relative">
      {/* Background Glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-indigo-600/20 rounded-full blur-[120px] pointer-events-none"></div>
      
      <header className="relative z-10 container mx-auto px-6 py-6 flex items-center justify-between">
        <div className="text-2xl font-bold tracking-tight text-white">FeatureFlow<span className="text-indigo-500">.</span></div>
        <div className="flex items-center gap-6">
          <Link to="/platform/dashboard" className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-medium text-white transition-colors">Launch Platform</Link>
        </div>
      </header>

      <main className="relative z-10 container mx-auto px-6 pt-32 pb-20 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm font-medium mb-8">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
          FeatureFlow v1.0 is now live
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8">
          Enterprise MLOps <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">Simplified.</span>
        </h1>
        
        <p className="text-lg md:text-xl text-neutral-400 max-w-2xl mx-auto mb-12">
          Deploy, monitor, and scale your machine learning models with confidence. A unified platform for feature stores, real-time inference, and data drift detection.
        </p>
        
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/platform/dashboard" className="w-full sm:w-auto px-8 py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold flex items-center justify-center gap-2 transition-all hover:scale-105">
            Launch FeatureFlow
            <ArrowRight size={20} />
          </Link>
          <a href="#features" className="w-full sm:w-auto px-8 py-4 rounded-xl bg-neutral-900 border border-neutral-800 hover:bg-neutral-800 text-white font-semibold transition-all">
            View Features
          </a>
        </div>
      </main>

      {/* Features Grid */}
      <section id="features" className="relative z-10 container mx-auto px-6 py-20 border-t border-neutral-800/50">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="p-8 rounded-3xl bg-neutral-900/50 border border-neutral-800 backdrop-blur-sm">
            <div className="w-12 h-12 rounded-xl bg-indigo-500/20 text-indigo-400 flex items-center justify-center mb-6">
              <Cpu size={24} />
            </div>
            <h3 className="text-xl font-bold mb-3">Real-time Inference</h3>
            <p className="text-neutral-400 leading-relaxed">Serve models globally with sub-millisecond latency. Built on a highly concurrent asynchronous engine.</p>
          </div>
          <div className="p-8 rounded-3xl bg-neutral-900/50 border border-neutral-800 backdrop-blur-sm">
            <div className="w-12 h-12 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center mb-6">
              <Activity size={24} />
            </div>
            <h3 className="text-xl font-bold mb-3">Drift Detection</h3>
            <p className="text-neutral-400 leading-relaxed">Automatically detect data drift and data quality issues before they impact your business metrics.</p>
          </div>
          <div className="p-8 rounded-3xl bg-neutral-900/50 border border-neutral-800 backdrop-blur-sm">
            <div className="w-12 h-12 rounded-xl bg-blue-500/20 text-blue-400 flex items-center justify-center mb-6">
              <Shield size={24} />
            </div>
            <h3 className="text-xl font-bold mb-3">Enterprise Security</h3>
            <p className="text-neutral-400 leading-relaxed">Role-based access control, detailed audit logs, and secure JWT authentication for every API call.</p>
          </div>
        </div>
      </section>
    </div>
  );
};
