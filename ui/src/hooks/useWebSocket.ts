/**
 * WebSocket hook for real-time game state updates.
 */

import { useCallback, useEffect, useRef } from "react";
import { useGameStore } from "../stores/gameStore";
import type {
  AgentThought,
  ControlCommand,
  GameEvent,
  HistoryData,
  WebSocketMessage,
} from "../types/game";

// WebSocket URL - in production, derive from window.location
const getWsUrl = () => {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host || "localhost:8000";
  return `${protocol}//${host}/ws/game-state`;
};

const RECONNECT_DELAY = 3000;
const PING_INTERVAL = 30000;

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | undefined>(undefined);
  const pingIntervalRef = useRef<number | undefined>(undefined);

  const { setConnected, updateState, addThought, addEvent, setHistory } =
    useGameStore();

  const connect = useCallback(() => {
    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = getWsUrl();
    console.log("Connecting to WebSocket:", wsUrl);

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WebSocket connected");
      setConnected(true);

      // Start ping interval
      pingIntervalRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "PING" }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        switch (message.type) {
          case "STATE_UPDATE": {
            const data = message.data as {
              game: Parameters<typeof updateState>[0];
              engine: Parameters<typeof updateState>[1];
              screen: string;
            };
            if (data) {
              updateState(data.game, data.engine, data.screen);
            }
            break;
          }

          case "AGENT_THOUGHT": {
            const thought = message.data as AgentThought;
            if (thought) {
              addThought(thought);
            }
            break;
          }

          case "EVENT": {
            const gameEvent = message.data as GameEvent;
            if (gameEvent) {
              addEvent(gameEvent);
            }
            break;
          }

          case "HISTORY": {
            const history = message.data as HistoryData;
            if (history) {
              setHistory(history.thoughts || [], history.events || []);
            }
            break;
          }

          case "PING":
            ws.send(JSON.stringify({ type: "PONG" }));
            break;

          case "PONG":
            // Server responded to our ping
            break;

          case "COMMAND_ACK":
            console.log("Command acknowledged:", message.data);
            break;

          case "ERROR":
            console.error("WebSocket error:", message.data);
            break;

          default:
            console.log("Unknown message type:", message.type);
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setConnected(false);

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }

      // Schedule reconnection
      reconnectTimeoutRef.current = window.setTimeout(
        connect,
        RECONNECT_DELAY
      );
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }, [setConnected, updateState, addThought, addEvent, setHistory]);

  // Send a command to the server
  const sendCommand = useCallback((command: ControlCommand) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "COMMAND",
          command,
        })
      );
    } else {
      console.warn("WebSocket not connected, cannot send command");
    }
  }, []);

  // Convenience methods
  const pause = useCallback(() => {
    sendCommand({ type: "PAUSE" });
  }, [sendCommand]);

  const resume = useCallback(() => {
    sendCommand({ type: "RESUME" });
  }, [sendCommand]);

  const setSpeed = useCallback(
    (speed: number) => {
      sendCommand({ type: "SET_SPEED", payload: { speed } });
    },
    [sendCommand]
  );

  // Connect on mount, cleanup on unmount
  useEffect(() => {
    connect();

    return () => {
      // Cleanup
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    sendCommand,
    pause,
    resume,
    setSpeed,
  };
}
