/* ═══════════════════════════════════════════════════════════════
   DiaSentry — useWebSocket Hook
   Manages real-time WebSocket connection with auto-reconnect
   ═══════════════════════════════════════════════════════════════ */

import { useEffect, useRef, useState, useCallback } from "react";
import type { DashboardPayload } from "../lib/types";
import { WS_URL } from "../lib/constants";

interface UseWebSocketReturn {
  data: DashboardPayload | null;
  isConnected: boolean;
  send: (msg: object) => void;
  reconnect: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelay = useRef(1000);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectDelay.current = 1000; // Reset delay on successful connect
        console.log("✅ WebSocket connected to", WS_URL);
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as DashboardPayload;
          if (parsed.type === "glucose_update" || parsed.glucose) {
            setData(parsed);
          }
        } catch (e) {
          console.warn("Failed to parse WebSocket message:", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log("🔌 WebSocket disconnected. Reconnecting...");

        // Exponential backoff reconnect
        reconnectTimeout.current = setTimeout(() => {
          reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, 10000);
          connect();
        }, reconnectDelay.current);
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        ws.close();
      };
    } catch (e) {
      console.error("WebSocket connection failed:", e);
      reconnectTimeout.current = setTimeout(connect, reconnectDelay.current);
    }
  }, []);

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const reconnect = useCallback(() => {
    wsRef.current?.close();
    setTimeout(connect, 500);
  }, [connect]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeout.current) clearTimeout(reconnectTimeout.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { data, isConnected, send, reconnect };
}
