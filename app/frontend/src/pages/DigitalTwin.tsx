import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, { 
    Background, 
    Controls, 
    Edge, 
    Node,
    MarkerType,
    useNodesState,
    useEdgesState,
    Handle,
    Position
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useWebSocket } from '../contexts/WebSocketContext';
import { Database, Zap, Cpu, Server, Activity, ShieldCheck } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';

// Custom Node Component
const SystemNode = ({ data }: any) => {
    return (
        <div className={`px-4 py-3 shadow-lg rounded-md bg-[#1e1e1e] border-2 transition-all duration-300 ${
            data.isActive ? 'border-blue-500 shadow-blue-500/50 scale-105' : 'border-gray-700'
        } ${data.hasError ? 'border-red-500 shadow-red-500/50 scale-105' : ''}`}>
            <Handle type="target" position={Position.Top} className="w-16 !bg-gray-600" />
            <div className="flex items-center">
                <div className={`rounded-full p-2 mr-3 flex items-center justify-center ${
                    data.isActive ? 'bg-blue-500/20 text-blue-400' : 
                    data.hasError ? 'bg-red-500/20 text-red-400' : 'bg-gray-800 text-gray-400'
                }`}>
                    {data.icon}
                </div>
                <div>
                    <div className="text-sm font-bold text-gray-200">{data.label}</div>
                    <div className="text-xs text-gray-500 mt-1">{data.status}</div>
                </div>
            </div>
            <Handle type="source" position={Position.Bottom} className="w-16 !bg-gray-600" />
        </div>
    );
};

const nodeTypes = {
    systemNode: SystemNode,
};

const initialNodes: Node[] = [
    { id: 'data_ingestion', type: 'systemNode', position: { x: 250, y: 50 }, data: { label: 'Data Ingestion', icon: <Database size={18} />, status: 'Idle', isActive: false } },
    { id: 'feature_store', type: 'systemNode', position: { x: 250, y: 200 }, data: { label: 'Feature Store', icon: <Zap size={18} />, status: 'Online', isActive: false } },
    { id: 'training_engine', type: 'systemNode', position: { x: 50, y: 350 }, data: { label: 'Training Engine', icon: <Cpu size={18} />, status: 'Waiting for jobs', isActive: false } },
    { id: 'model_registry', type: 'systemNode', position: { x: 250, y: 500 }, data: { label: 'Model Registry', icon: <ShieldCheck size={18} />, status: 'Synced', isActive: false } },
    { id: 'inference_engine', type: 'systemNode', position: { x: 450, y: 350 }, data: { label: 'Inference Engine', icon: <Server size={18} />, status: 'Serving predictions', isActive: false } },
    { id: 'monitoring', type: 'systemNode', position: { x: 250, y: 650 }, data: { label: 'Drift & Monitoring', icon: <Activity size={18} />, status: 'Monitoring active', isActive: false } },
];

const initialEdges: Edge[] = [
    { id: 'e1-2', source: 'data_ingestion', target: 'feature_store', animated: true, style: { stroke: '#4b5563' } },
    { id: 'e2-3', source: 'feature_store', target: 'training_engine', animated: true, style: { stroke: '#4b5563' } },
    { id: 'e3-4', source: 'training_engine', target: 'model_registry', animated: true, style: { stroke: '#4b5563' } },
    { id: 'e2-5', source: 'feature_store', target: 'inference_engine', animated: true, style: { stroke: '#4b5563' } },
    { id: 'e4-5', source: 'model_registry', target: 'inference_engine', animated: true, style: { stroke: '#4b5563' } },
    { id: 'e5-6', source: 'inference_engine', target: 'monitoring', animated: true, style: { stroke: '#4b5563' } },
];

export const DigitalTwin = () => {
    const { events } = useWebSocket();
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    // Effect to map events to node animations
    useEffect(() => {
        if (events.length === 0) return;
        
        const latestEvent = events[0]; // Events are prepended, so 0 is newest
        
        setNodes((nds) => 
            nds.map((node) => {
                let isActive = false;
                let hasError = latestEvent.severity === 'error';
                let status = node.data.status;

                switch(latestEvent.type) {
                    case 'Dataset.Uploaded':
                    case 'Dataset.Validated':
                    case 'Dataset.Failed':
                        if (node.id === 'data_ingestion') {
                            isActive = true;
                            status = latestEvent.type;
                        }
                        break;
                    case 'Feature.Materialized':
                        if (node.id === 'feature_store') {
                            isActive = true;
                            status = 'Materializing features';
                        }
                        break;
                    case 'Job.Started':
                    case 'Job.Completed':
                    case 'Job.Failed':
                        if (node.id === 'training_engine') {
                            isActive = true;
                            status = latestEvent.type;
                        }
                        break;
                    case 'Model.Registered':
                    case 'Model.Promoted':
                        if (node.id === 'model_registry') {
                            isActive = true;
                            status = 'Registering / Promoting';
                        }
                        break;
                    case 'Inference.Requested':
                    case 'Inference.Completed':
                    case 'Inference.Failed':
                        if (node.id === 'inference_engine') {
                            isActive = true;
                            status = `Processing: ${latestEvent.payload?.latency_ms ? latestEvent.payload.latency_ms.toFixed(1) + 'ms' : 'req'}`;
                        }
                        break;
                    case 'Monitoring.LatencySpike':
                    case 'Monitoring.HealthChange':
                    case 'Feature.DriftDetected':
                        if (node.id === 'monitoring') {
                            isActive = true;
                            status = latestEvent.type;
                        }
                        break;
                }

                return {
                    ...node,
                    data: {
                        ...node.data,
                        isActive: isActive || node.data.isActive,
                        hasError: (isActive && hasError) || node.data.hasError,
                        status: status
                    }
                };
            })
        );

        // Turn off the active state after 2 seconds
        const timer = setTimeout(() => {
            setNodes((nds) => 
                nds.map(n => ({
                    ...n,
                    data: { ...n.data, isActive: false, hasError: false }
                }))
            );
        }, 2000);

        return () => clearTimeout(timer);
    }, [events, setNodes]);

    return (
        <div className="h-[calc(100vh-100px)] animate-in fade-in duration-500">
            <PageHeader 
                title="Digital Twin Topology" 
                subtitle="Live architectural representation of the MLOps Operating System." 
            />
            <div className="w-full h-full bg-[#121212] rounded-lg border border-gray-800 overflow-hidden shadow-2xl mt-4">
                <ReactFlow 
                    nodes={nodes} 
                    edges={edges} 
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    nodeTypes={nodeTypes}
                    fitView
                    attributionPosition="bottom-right"
                >
                    <Background color="#333" gap={16} />
                    <Controls className="bg-[#1e1e1e] border-gray-800 fill-gray-400" />
                </ReactFlow>
            </div>
        </div>
    );
};
