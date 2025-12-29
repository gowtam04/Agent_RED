/**
 * TypeScript types for the Pokemon Red AI Agent dashboard.
 */

// Game mode types
export type GameMode = "OVERWORLD" | "BATTLE" | "MENU" | "DIALOGUE";

// Agent types
export type AgentType = "ORCHESTRATOR" | "NAVIGATION" | "BATTLE" | "MENU";

// Position data
export interface Position {
  map_id: string;
  map_name: string;
  x: number;
  y: number;
  facing: string;
}

// Pokemon status in party
export interface PokemonStatus {
  species: string;
  level: number;
  hp: number;
  max_hp: number;
  status: string | null;
}

// Battle data
export interface BattleData {
  battle_type: string;
  enemy_species: string;
  enemy_level: number;
  enemy_hp_percent: number;
}

// Objective in the stack
export interface Objective {
  type: string;
  target: string;
  priority: number;
}

// Full game state data
export interface GameData {
  mode: GameMode;
  position: Position;
  party: PokemonStatus[];
  in_battle: boolean;
  battle: BattleData | null;
  money: number;
  badges: string[];
}

// Engine/runtime state data
export interface EngineData {
  running: boolean;
  paused: boolean;
  current_agent: AgentType | string;
  objective_stack: Objective[];
  total_frames: number;
  api_calls: number;
  uptime_seconds: number;
}

// Agent thought/reasoning
export interface AgentThought {
  timestamp: string;
  agent_type: AgentType | string;
  reasoning: string;
  action: string;
  result_data?: Record<string, unknown>;
}

// Game event
export interface GameEvent {
  timestamp: string;
  event_type: string;
  description: string;
  data?: Record<string, unknown>;
}

// Full state update from WebSocket
export interface StateUpdate {
  type: "STATE_UPDATE";
  game: GameData;
  engine: EngineData;
  screen: string; // Base64 PNG
}

// WebSocket message types
export type WebSocketMessageType =
  | "STATE_UPDATE"
  | "AGENT_THOUGHT"
  | "EVENT"
  | "HISTORY"
  | "PING"
  | "PONG"
  | "COMMAND_ACK"
  | "ERROR";

export interface WebSocketMessage<T = unknown> {
  type: WebSocketMessageType;
  data?: T;
}

// History payload (sent on connect)
export interface HistoryData {
  thoughts: AgentThought[];
  events: GameEvent[];
}

// Control command types
export type ControlCommandType = "SET_SPEED" | "PAUSE" | "RESUME";

export interface ControlCommand {
  type: ControlCommandType;
  payload?: Record<string, unknown>;
}
