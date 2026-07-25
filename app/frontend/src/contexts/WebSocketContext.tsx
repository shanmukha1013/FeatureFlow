import React, { createContext, useContext, useEffect, useState, ReactNode, useRef } from 'react';

export interface PlatformEvent {
    id: string;
    type: string;
    timestamp: string;
    source: string;
    severity: string;
    payload: any;
    correlation_id?: string;
}

interface WebSocketContextType {
    events: PlatformEvent[];
    isConnected: boolean;
    clearEvents: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [events, setEvents] = useState<PlatformEvent[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);

    useEffect(() => {
        // Connect to the WebSocket endpoint
        // Since we proxy `/api` in vite, we might need a separate proxy for ws or just use relative protocol
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Connect to vite proxy or direct backend if compiled
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/events`;
        
        // Wait, the backend route is actually at `/ws/events` or `/api/v1/ws/events`?
        // Let's use standard URL constructor
        let wsEndpoint = '/api/v1/ws/events'; // adjust based on where the router is mounted
        if (import.meta.env.DEV) {
            wsEndpoint = 'ws://localhost:8000/ws/events'; // Vite proxy might not handle raw WS well without config, connecting directly to backend
        } else {
            wsEndpoint = `${protocol}//${window.location.host}/ws/events`;
        }

        const connect = () => {
            console.log("Connecting to WebSocket:", wsEndpoint);
            const ws = new WebSocket(wsEndpoint);

            ws.onopen = () => {
                setIsConnected(true);
                console.log("WebSocket connected.");
            };

            ws.onmessage = (event) => {
                try {
                    const parsedEvent: PlatformEvent = JSON.parse(event.data);
                    setEvents(prev => [parsedEvent, ...prev].slice(0, 500)); // Keep last 500 events
                } catch (e) {
                    console.error("Failed to parse event data", e);
                }
            };

            ws.onclose = () => {
                setIsConnected(false);
                console.log("WebSocket disconnected. Retrying in 5 seconds...");
                setTimeout(connect, 5000);
            };

            ws.onerror = (err) => {
                console.error("WebSocket error:", err);
                ws.close();
            };

            wsRef.current = ws;
        };

        connect();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);

    const clearEvents = () => setEvents([]);

    return (
        <WebSocketContext.Provider value={{ events, isConnected, clearEvents }}>
            {children}
        </WebSocketContext.Provider>
    );
};

export const useWebSocket = () => {
    const context = useContext(WebSocketContext);
    if (context === undefined) {
        throw new Error('useWebSocket must be used within a WebSocketProvider');
    }
    return context;
};
