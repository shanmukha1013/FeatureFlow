import React from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { Terminal, Activity, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';

export const EventStream: React.FC = () => {
    const { events, isConnected } = useWebSocket();

    const getSeverityIcon = (severity: string) => {
        switch (severity.toLowerCase()) {
            case 'error':
            case 'critical':
                return <AlertTriangle className="w-4 h-4 text-red-400" />;
            case 'warning':
                return <Activity className="w-4 h-4 text-amber-400" />;
            case 'success':
            case 'info':
            default:
                return <Info className="w-4 h-4 text-blue-400" />;
        }
    };

    return (
        <div className="bg-[#1e1e1e] border border-gray-800 rounded-lg flex flex-col h-full overflow-hidden font-mono text-sm shadow-xl">
            {/* Header */}
            <div className="bg-[#2d2d2d] px-4 py-3 flex items-center justify-between border-b border-gray-800">
                <div className="flex items-center space-x-2">
                    <Terminal className="w-5 h-5 text-gray-400" />
                    <h3 className="font-semibold text-gray-200 tracking-wider text-xs">LIVE EVENT STREAM</h3>
                </div>
                <div className="flex items-center space-x-2">
                    <span className="text-xs text-gray-500">Status:</span>
                    {isConnected ? (
                        <div className="flex items-center space-x-1">
                            <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                            </span>
                            <span className="text-emerald-400 text-xs font-semibold">CONNECTED</span>
                        </div>
                    ) : (
                        <div className="flex items-center space-x-1">
                            <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                            <span className="text-red-400 text-xs font-semibold">DISCONNECTED</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Event List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-[#151515]">
                {events.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-gray-600 italic">
                        Listening for platform events...
                    </div>
                ) : (
                    events.map((event) => (
                        <div key={event.id} className="group relative rounded-md border border-gray-800/50 bg-[#1e1e1e] p-3 hover:border-blue-500/30 transition-colors">
                            <div className="flex items-start justify-between mb-2">
                                <div className="flex items-center space-x-2">
                                    {getSeverityIcon(event.severity)}
                                    <span className="font-bold text-gray-200">{event.type}</span>
                                </div>
                                <span className="text-xs text-gray-500">
                                    {new Date(event.timestamp).toLocaleTimeString()}
                                </span>
                            </div>
                            <div className="text-xs text-gray-400 mb-1 flex justify-between">
                                <span><span className="text-gray-600">SRC:</span> {event.source}</span>
                                <span className="text-gray-600 font-mono text-[10px]">{event.id.split('-')[0]}</span>
                            </div>
                            {event.payload && Object.keys(event.payload).length > 0 && (
                                <div className="mt-2 bg-[#121212] p-2 rounded text-xs text-green-400 overflow-x-auto border border-gray-900 shadow-inner whitespace-pre-wrap break-all">
                                    {JSON.stringify(event.payload, null, 2)}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};
