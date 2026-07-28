import React, { useEffect, useState, useCallback, useMemo } from 'react';
import ReactFlow, { 
  MiniMap, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState,
  MarkerType,
  Handle,
  Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { apiClient as api } from '../api/client';
import { 
  Database, Box, PlayCircle, FileJson, 
  AlertTriangle, Lightbulb, CheckCircle2 
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

// Custom Node Component to display Intelligence
const IntelligentNode = ({ data }) => {
  const navigate = useNavigate();

  const getIcon = () => {
    switch(data.type) {
      case 'dataset': return <Database size={16} className="text-blue-400" />;
      case 'feature_group': return <FileJson size={16} className="text-purple-400" />;
      case 'model': return <Box size={16} className="text-emerald-400" />;
      case 'endpoint': return <PlayCircle size={16} className="text-orange-400" />;
      default: return null;
    }
  };

  const navigateToDeepDive = () => {
    // Navigate to deep dive based on type
    if (data.type === 'dataset') navigate(`/platform/datasets`);
    if (data.type === 'feature_group') navigate(`/platform/features`);
    if (data.type === 'model') navigate(`/platform/models`);
    if (data.type === 'endpoint') navigate(`/platform/inference`);
  };

  return (
    <div 
      className="bg-[#121212] border border-[#2a2a2a] rounded-lg p-3 min-w-[250px] max-w-[300px] shadow-lg cursor-pointer hover:border-indigo-500 transition-colors"
      onClick={navigateToDeepDive}
    >
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-gray-500" />
      
      <div className="flex items-center gap-2 mb-2 border-b border-[#2a2a2a] pb-2">
        {getIcon()}
        <span className="text-sm font-semibold text-gray-200">{data.label}</span>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-500 uppercase font-mono tracking-wider">Status</span>
          <span className="text-emerald-400 font-mono">{data.metadata?.status || 'UNKNOWN'}</span>
        </div>
        
        {data.metadata?.count !== undefined && (
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 uppercase font-mono tracking-wider">Count</span>
            <span className="text-gray-300 font-mono">{data.metadata.count}</span>
          </div>
        )}
      </div>

      {/* Intelligence & Recommendations Section */}
      {data.metadata?.recommendations && data.metadata.recommendations.length > 0 && (
        <div className="mt-3 bg-[#1a1a1a] rounded p-2 border border-indigo-500/30">
          <div className="flex items-center gap-1.5 mb-1">
            <Lightbulb size={12} className="text-indigo-400" />
            <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400">Copilot</span>
          </div>
          <ul className="text-xs text-gray-400 space-y-1">
            {data.metadata.recommendations.map((rec, i) => (
              <li key={i} className="flex items-start gap-1">
                <span className="text-indigo-500 mt-0.5">•</span>
                <span className="leading-tight">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-gray-500" />
    </div>
  );
};

const nodeTypes = {
  intelligent: IntelligentNode,
};

export const LifecycleCanvas = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);

  const fetchLineage = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get('/management/lineage/groups');
      const data = res.data;

      // Layout nodes horizontally
      const xOffset = 350;
      const yOffset = 150;
      
      const formattedNodes = data.nodes.map((n, i) => {
        // Very basic layout: group by type
        let col = 0;
        if (n.type === 'dataset') col = 0;
        if (n.type === 'feature_group') col = 1;
        if (n.type === 'model') col = 2;
        if (n.type === 'endpoint') col = 3;

        // Count how many in this column before this one for Y pos
        const sameTypeIndex = data.nodes.slice(0, i).filter(prev => prev.type === n.type).length;

        return {
          id: n.id,
          type: 'intelligent',
          data: n,
          position: { x: col * xOffset, y: sameTypeIndex * yOffset + 50 }
        };
      });

      const formattedEdges = data.edges.map(e => ({
        id: e.id,
        source: e.source,
        target: e.target,
        animated: true,
        style: { stroke: '#6366f1', strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#6366f1',
        },
      }));

      setNodes(formattedNodes);
      setEdges(formattedEdges);
    } catch (err) {
      console.error("Failed to load lineage", err);
    } finally {
      setLoading(false);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    fetchLineage();
    // Simulate real-time updates every 10s for the Copilot
    const interval = setInterval(fetchLineage, 10000);
    return () => clearInterval(interval);
  }, [fetchLineage]);

  if (loading && nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-gray-400">Loading Intelligent Canvas...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]">
      <div className="mb-4">
        <h1 className="text-2xl font-bold text-white mb-1">Lifecycle Canvas</h1>
        <p className="text-sm text-gray-400">Intelligent orchestration of your ML pipelines.</p>
      </div>
      <div className="flex-1 rounded-xl border border-[#1f1f1f] bg-[#0d0d0d] overflow-hidden shadow-2xl relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-right"
        >
          <Background color="#222" gap={24} size={1} />
          <Controls className="!bg-[#1a1a1a] !border-[#2a2a2a] !fill-gray-400" />
        </ReactFlow>
      </div>
    </div>
  );
};
