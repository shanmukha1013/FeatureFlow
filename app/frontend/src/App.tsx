import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Inference } from './pages/Inference';
import { Models } from './pages/Models';
import { AuditLogs } from './pages/AuditLogs';
import { Datasets } from './pages/Datasets';
import { Features } from './pages/Features';
import { Pipelines } from './pages/Pipelines';
import { Health } from './pages/Health';
import { Settings } from './pages/Settings';
import { Monitoring } from './pages/Monitoring';

const App = () => {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="inference" element={<Inference />} />
        <Route path="models" element={<Models />} />
        <Route path="monitoring" element={<Monitoring />} />
        <Route path="audit" element={<AuditLogs />} />
        <Route path="datasets" element={<Datasets />} />
        <Route path="features" element={<Features />} />
        <Route path="pipelines" element={<Pipelines />} />
        <Route path="health" element={<Health />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
};

export default App;
