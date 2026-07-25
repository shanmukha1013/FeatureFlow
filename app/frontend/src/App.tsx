import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { LifecycleCanvas } from './pages/LifecycleCanvas';
import { Inference } from './pages/Inference';
import { Models } from './pages/Models';
import { AuditLogs } from './pages/AuditLogs';
import { Explainability } from './pages/Explainability';
import { Drift } from './pages/Drift';
import { Retraining } from './pages/Retraining';
import { Enterprise } from './pages/Enterprise';
import { Datasets } from './pages/Datasets';
import { Features } from './pages/Features';
import { Pipelines } from './pages/Pipelines';
import { Settings } from './pages/Settings';
import { Monitoring } from './pages/Monitoring';
import { Training } from './pages/Training';

import { PlatformProvider } from './contexts/PlatformContext';
import { WebSocketProvider } from './contexts/WebSocketContext';

const App = () => {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/platform/canvas" replace />} />
        <Route path="/platform" element={
            <PlatformProvider>
              <WebSocketProvider>
                <AppLayout />
              </WebSocketProvider>
            </PlatformProvider>
        }>
          <Route path="canvas" element={<LifecycleCanvas />} />
          <Route path="enterprise" element={<Enterprise />} />
          <Route path="training" element={<Training />} />
          <Route path="retraining" element={<Retraining />} />
          <Route path="inference" element={<Inference />} />
          <Route path="explainability" element={<Explainability />} />
          <Route path="drift" element={<Drift />} />
          <Route path="models" element={<Models />} />
          <Route path="monitoring" element={<Monitoring />} />
          <Route path="audit" element={<AuditLogs />} />
          <Route path="datasets" element={<Datasets />} />
          <Route path="features" element={<Features />} />
          <Route path="pipelines" element={<Pipelines />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/platform/canvas" replace />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
};

export default App;
