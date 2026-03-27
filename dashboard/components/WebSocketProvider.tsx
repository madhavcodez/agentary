"use client";

import { createContext, useContext, type ReactNode } from "react";
import {
  useWebSocket,
  type ConnectionState,
} from "@/lib/hooks/useWebSocket";
import { isAuthenticated } from "@/lib/auth";
import type { WSEvent } from "@/lib/types/events";

type EventHandler = (event: WSEvent) => void;

interface WebSocketContextValue {
  connectionState: ConnectionState;
  subscribe: (eventType: string, handler: EventHandler) => () => void;
}

const WebSocketContext = createContext<WebSocketContextValue>({
  connectionState: "disconnected",
  subscribe: () => () => {},
});

export function WebSocketProvider({ children }: { children: ReactNode }) {
  // Only attempt WS connection if user has a token
  const ws = useWebSocket({ enabled: isAuthenticated() });
  return (
    <WebSocketContext.Provider value={ws}>{children}</WebSocketContext.Provider>
  );
}

export function useWS(): WebSocketContextValue {
  return useContext(WebSocketContext);
}
