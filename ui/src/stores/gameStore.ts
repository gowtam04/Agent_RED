/**
 * Zustand store for game state management.
 */

import { create } from "zustand";
import type {
  AgentThought,
  EngineData,
  GameData,
  GameEvent,
} from "../types/game";

// Maximum items to keep in history
const MAX_THOUGHTS = 50;
const MAX_EVENTS = 100;

interface GameStore {
  // Connection state
  connected: boolean;
  setConnected: (connected: boolean) => void;

  // Game state
  game: GameData | null;
  engine: EngineData | null;
  screen: string | null;

  // History
  thoughts: AgentThought[];
  events: GameEvent[];

  // Actions
  updateState: (game: GameData, engine: EngineData, screen: string) => void;
  addThought: (thought: AgentThought) => void;
  addEvent: (event: GameEvent) => void;
  setHistory: (thoughts: AgentThought[], events: GameEvent[]) => void;
  clearHistory: () => void;
}

export const useGameStore = create<GameStore>((set) => ({
  // Initial state
  connected: false,
  game: null,
  engine: null,
  screen: null,
  thoughts: [],
  events: [],

  // Connection
  setConnected: (connected) => set({ connected }),

  // State update
  updateState: (game, engine, screen) =>
    set({
      game,
      engine,
      screen,
    }),

  // Add thought (keeping max items)
  addThought: (thought) =>
    set((state) => ({
      thoughts: [...state.thoughts.slice(-(MAX_THOUGHTS - 1)), thought],
    })),

  // Add event (keeping max items)
  addEvent: (event) =>
    set((state) => ({
      events: [...state.events.slice(-(MAX_EVENTS - 1)), event],
    })),

  // Set history (from initial WebSocket connection)
  setHistory: (thoughts, events) =>
    set({
      thoughts: thoughts.slice(-MAX_THOUGHTS),
      events: events.slice(-MAX_EVENTS),
    }),

  // Clear history
  clearHistory: () => set({ thoughts: [], events: [] }),
}));
