"""Navigation agent for overworld movement and pathfinding."""

from typing import Any

from src.knowledge import HMRequirements, MapData
from src.tools import NAVIGATION_TOOLS

from .base import BaseAgent
from .state import GameState
from .types import AgentResult, AgentType, ModelType

NAVIGATION_SYSTEM_PROMPT = """You are the Navigation agent for a Pokemon Red AI system.

Your responsibilities:
1. Move the player through the overworld
2. Find optimal paths using A* pathfinding
3. Avoid unwanted trainer battles when possible
4. Use HM moves to clear obstacles (Cut, Surf, Strength)
5. Handle wild encounters (flee or fight based on objective)

You have access to these tools:
- get_current_position: Get player location
- get_map_data: Get map layout and objects
- find_path: Calculate path to destination
- get_interactables: Find nearby objects/NPCs
- execute_movement: Send movement inputs
- check_route_accessibility: Check HM requirements
- get_hidden_items: Find hidden items on map
- use_hm_in_field: Use Cut/Surf/Strength/Flash

Movement principles:
1. Minimize grass tiles to reduce encounters
2. Avoid trainer line-of-sight when not grinding
3. Pick up visible items when convenient
4. Use warps and connections efficiently

If movement is interrupted by a wild encounter, report back and let Battle agent handle it.
"""


class NavigationAgent(BaseAgent):
    """Agent for handling overworld navigation."""

    AGENT_TYPE: AgentType = "NAVIGATION"
    DEFAULT_MODEL: ModelType = "haiku"
    SYSTEM_PROMPT: str = NAVIGATION_SYSTEM_PROMPT

    def __init__(
        self,
        client: Any | None = None,
        model: ModelType | None = None,
    ):
        super().__init__(client, model)
        self._map_data = MapData()
        self._hm_requirements = HMRequirements()
        self._emulator: Any = None
        self._state_reader: Any = None

    def _register_tools(self) -> list[dict[str, Any]]:
        """Return navigation tool definitions."""
        return NAVIGATION_TOOLS

    def _get_emulator(self) -> Any:
        """Get emulator instance, returns None if not available.

        Note: EmulatorInterface is not a singleton. This method returns
        the emulator if it was set via set_emulator(), otherwise None.
        """
        return self._emulator

    def set_emulator(self, emulator: Any) -> None:
        """Set the emulator instance for this agent."""
        self._emulator = emulator
        # Also create state reader if emulator is set
        if emulator:
            try:
                from src.emulator.state_reader import StateReader

                self._state_reader = StateReader(emulator)
            except Exception:
                pass

    def _get_state_reader(self) -> Any:
        """Get state reader instance, returns None if not available."""
        return self._state_reader

    def act(self, state: GameState) -> AgentResult:
        """Take a navigation action based on current state."""
        # Format state for Claude
        state_str = self._format_state_for_prompt(state)

        # Add navigation-specific context
        state_str += "\n\n=== NAVIGATION CONTEXT ==="
        state_str += f"\nCurrent Map: {state.position.map_id}"
        state_str += f"\nPosition: ({state.position.x}, {state.position.y})"
        state_str += f"\nFacing: {state.position.facing}"
        state_str += f"\nHMs usable: {', '.join(state.hms_usable) if state.hms_usable else 'None'}"

        # Build messages
        messages = [{"role": "user", "content": state_str}]

        # Call Claude
        response = self._call_claude(messages)

        # Process tool calls
        return self._process_tool_calls(response, state)

    def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        state: GameState,
    ) -> AgentResult:
        """Execute a navigation tool."""
        tool_handlers = {
            "get_current_position": self._get_current_position,
            "get_map_data": self._get_map_data,
            "find_path": self._find_path,
            "get_interactables": self._get_interactables,
            "execute_movement": self._execute_movement,
            "check_route_accessibility": self._check_route_accessibility,
            "get_hidden_items": self._get_hidden_items,
            "use_hm_in_field": self._use_hm_in_field,
        }

        handler = tool_handlers.get(tool_name)
        if handler:
            return handler(tool_input, state)

        return AgentResult(
            success=False,
            action_taken=tool_name,
            error=f"Unknown tool: {tool_name}",
        )

    def _get_current_position(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get current player position from state or memory."""
        state_reader = self._get_state_reader()

        if state_reader:
            try:
                position = state_reader.get_position()
                return AgentResult(
                    success=True,
                    action_taken="get_current_position",
                    result_data={
                        "map_id": position.map_id,
                        "x": position.x,
                        "y": position.y,
                        "facing": position.facing,
                        "source": "memory",
                    },
                )
            except Exception:
                pass

        # Fall back to state
        return AgentResult(
            success=True,
            action_taken="get_current_position",
            result_data={
                "map_id": state.position.map_id,
                "x": state.position.x,
                "y": state.position.y,
                "facing": state.position.facing,
                "source": "cached_state",
            },
        )

    def _get_map_data(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get map layout and objects from knowledge base."""
        map_id = tool_input.get("map_id") or state.position.map_id
        include_tiles = tool_input.get("include_tiles", False)
        include_npcs = tool_input.get("include_npcs", True)

        map_info = self._map_data.get(map_id)

        if not map_info:
            return AgentResult(
                success=False,
                action_taken="get_map_data",
                error=f"Map not found: {map_id}",
            )

        result = {
            "map_id": map_id,
            "name": map_info.get("name", map_id),
            "width": map_info.get("width", 0),
            "height": map_info.get("height", 0),
            "connections": map_info.get("connections", {}),
            "warps": map_info.get("warps", []),
        }

        if include_tiles:
            result["tiles"] = map_info.get("tiles", [])

        if include_npcs:
            result["npcs"] = map_info.get("objects", [])
            result["trainers"] = map_info.get("trainers", [])

        result["items"] = map_info.get("items", [])
        result["has_encounters"] = map_info.get("has_wild_encounters", False)

        return AgentResult(
            success=True,
            action_taken="get_map_data",
            result_data=result,
        )

    def _find_path(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Find path to destination using A* pathfinding.

        Uses the pathfinding module to calculate optimal routes, supporting:
        - Single-map A* pathfinding
        - Cross-map routing through connections and warps
        - Grass avoidance (encounter minimization)
        - Trainer vision avoidance
        - HM obstacle handling
        """
        from src.pathfinding import CrossMapRouter, TileWeights

        destination = tool_input["destination"]
        from_pos = tool_input.get("from") or {
            "map": state.position.map_id,
            "x": state.position.x,
            "y": state.position.y,
        }
        preferences = tool_input.get(
            "preferences",
            {
                "avoid_grass": True,
                "avoid_trainers": True,
            },
        )

        # Build tile weights from preferences
        weights = TileWeights()
        if preferences.get("avoid_grass", True):
            weights.grass = 5.0
        else:
            weights.grass = 1.0

        if preferences.get("avoid_trainers", True):
            weights.trainer_adjacent = 100.0
        else:
            weights.trainer_adjacent = 1.0

        # Get available HMs
        hms_available = preferences.get("allowed_hms") or list(state.hms_usable or [])

        # Get defeated trainers for avoidance
        defeated_trainers = set(state.defeated_trainers or [])

        # Use cross-map router for pathfinding
        router = CrossMapRouter()
        result = router.find_path(
            from_map=from_pos.get("map", ""),
            from_x=from_pos.get("x", 0),
            from_y=from_pos.get("y", 0),
            to_map=destination.get("map", ""),
            to_x=destination.get("x"),
            to_y=destination.get("y"),
            hms_available=hms_available,
            weights=weights,
            defeated_trainers=defeated_trainers,
        )

        if result.success:
            # Flatten moves from all segments
            all_moves = []
            for map_id, moves in result.segments:
                all_moves.extend(moves)

            return AgentResult(
                success=True,
                action_taken="find_path",
                result_data={
                    "path_found": True,
                    "total_steps": result.total_moves,
                    "moves": all_moves,
                    "segments": [
                        {"map": map_id, "moves": moves, "move_count": len(moves)}
                        for map_id, moves in result.segments
                    ],
                    "maps_traversed": result.maps_traversed,
                    "hms_required": result.hms_required,
                },
            )
        else:
            return AgentResult(
                success=True,
                action_taken="find_path",
                result_data={
                    "path_found": False,
                    "reason": "No valid path found",
                    "destination": destination,
                    "maps_attempted": result.maps_traversed,
                },
            )

    def _get_interactables(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get nearby interactable objects."""
        scan_range = tool_input.get("range", 5)

        map_info = self._map_data.get(state.position.map_id)
        if not map_info:
            return AgentResult(
                success=True,
                action_taken="get_interactables",
                result_data={"interactables": [], "map_not_found": True},
            )

        player_x = state.position.x
        player_y = state.position.y

        interactables = []

        # Check NPCs
        for npc in map_info.get("objects", []):
            npc_x = npc.get("x", 0)
            npc_y = npc.get("y", 0)
            if abs(npc_x - player_x) <= scan_range and abs(npc_y - player_y) <= scan_range:
                interactables.append(
                    {
                        "type": "npc",
                        "x": npc_x,
                        "y": npc_y,
                        "distance": abs(npc_x - player_x) + abs(npc_y - player_y),
                        "info": npc.get("name", "NPC"),
                    }
                )

        # Check items
        for item in map_info.get("items", []):
            item_x = item.get("x", 0)
            item_y = item.get("y", 0)
            if abs(item_x - player_x) <= scan_range and abs(item_y - player_y) <= scan_range:
                interactables.append(
                    {
                        "type": "item",
                        "x": item_x,
                        "y": item_y,
                        "distance": abs(item_x - player_x) + abs(item_y - player_y),
                        "item": item.get("item", "Unknown"),
                    }
                )

        # Check warps
        for warp in map_info.get("warps", []):
            warp_x = warp.get("x", 0)
            warp_y = warp.get("y", 0)
            if abs(warp_x - player_x) <= scan_range and abs(warp_y - player_y) <= scan_range:
                interactables.append(
                    {
                        "type": "warp",
                        "x": warp_x,
                        "y": warp_y,
                        "distance": abs(warp_x - player_x) + abs(warp_y - player_y),
                        "destination": warp.get("destination", "Unknown"),
                    }
                )

        # Sort by distance
        interactables.sort(key=lambda x: x["distance"])

        return AgentResult(
            success=True,
            action_taken="get_interactables",
            result_data={
                "interactables": interactables,
                "count": len(interactables),
                "player_position": {"x": player_x, "y": player_y},
            },
        )

    def _execute_movement(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Execute movement sequence."""
        moves = tool_input["moves"]
        stop_conditions = tool_input.get(
            "stop_conditions", ["BATTLE_START", "DIALOGUE_START", "WARP"]
        )
        frame_delay = tool_input.get("frame_delay", 4)

        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="execute_movement",
                result_data={
                    "moves_requested": len(moves),
                    "moves_completed": 0,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        state_reader = self._get_state_reader()
        initial_map = state.position.map_id

        moves_completed = 0
        stopped_reason = None

        try:
            for move in moves:
                # Execute the move
                if move in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    emulator.move(move.lower(), 1)
                else:
                    emulator.press_button(move.lower())

                # Wait frames
                emulator.tick(frame_delay)

                # Check stop conditions
                if state_reader:
                    try:
                        game_mode = state_reader.get_game_mode()

                        if "BATTLE_START" in stop_conditions and game_mode.value == "BATTLE":
                            stopped_reason = "BATTLE_START"
                            break

                        if "DIALOGUE_START" in stop_conditions and game_mode.value == "DIALOGUE":
                            stopped_reason = "DIALOGUE_START"
                            break

                        if "WARP" in stop_conditions:
                            current_pos = state_reader.get_position()
                            if current_pos.map_id != initial_map:
                                stopped_reason = "WARP"
                                break
                    except Exception:
                        pass

                moves_completed += 1

            # Get new position
            new_position = None
            if state_reader:
                try:
                    pos = state_reader.get_position()
                    new_position = {
                        "map_id": pos.map_id,
                        "x": pos.x,
                        "y": pos.y,
                        "facing": pos.facing,
                    }
                except Exception:
                    pass

            return AgentResult(
                success=True,
                action_taken="execute_movement",
                result_data={
                    "moves_completed": moves_completed,
                    "moves_total": len(moves),
                    "stopped_reason": stopped_reason,
                    "new_position": new_position,
                },
                handoff_to="BATTLE" if stopped_reason == "BATTLE_START" else None,
            )

        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="execute_movement",
                error=str(e),
                result_data={
                    "moves_completed": moves_completed,
                    "moves_total": len(moves),
                },
            )

    def _check_route_accessibility(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Check if a route is accessible with current HMs/badges."""
        from_map = tool_input["from_map"]
        to_map = tool_input["to_map"]
        available_hms = tool_input.get("available_hms", state.hms_usable)
        story_flags = tool_input.get("story_flags", state.story_flags)

        # Route accessibility checking is simplified for now
        # Full route requirements would need map connection data
        requirements: list[dict[str, str]] = []

        # Check each requirement
        missing: list[dict[str, str]] = []
        for req in requirements:
            req_type = req.get("type")
            req_value = req.get("value")

            if req_type == "hm":
                if req_value and req_value not in available_hms:
                    missing.append({"type": "hm", "need": req_value or ""})
            elif req_type == "story_flag":
                if req_value and req_value not in story_flags:
                    missing.append({"type": "story_flag", "need": req_value or ""})
            elif req_type == "badge":
                if req_value and req_value not in state.badges:
                    missing.append({"type": "badge", "need": req_value or ""})

        accessible = len(missing) == 0

        return AgentResult(
            success=True,
            action_taken="check_route_accessibility",
            result_data={
                "accessible": accessible,
                "from": from_map,
                "to": to_map,
                "requirements": requirements,
                "missing": missing,
            },
        )

    def _get_hidden_items(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get hidden item locations on current map."""
        map_id = tool_input.get("map_id") or state.position.map_id
        _only_unobtained = tool_input.get("only_unobtained", True)

        map_info = self._map_data.get(map_id)
        if not map_info:
            return AgentResult(
                success=True,
                action_taken="get_hidden_items",
                result_data={
                    "map_id": map_id,
                    "hidden_items": [],
                    "map_not_found": True,
                },
            )

        hidden_items = map_info.get("hidden_items", [])

        # Would filter by obtained items if tracking that
        # For now return all hidden items

        return AgentResult(
            success=True,
            action_taken="get_hidden_items",
            result_data={
                "map_id": map_id,
                "hidden_items": hidden_items,
                "count": len(hidden_items),
            },
        )

    def _use_hm_in_field(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Use an HM move in the overworld."""
        hm_move = tool_input["hm_move"]
        target_direction = tool_input.get("target_direction", "CURRENT")
        fly_destination = tool_input.get("fly_destination")

        # Check if we can use this HM
        hm_map = {
            "CUT": "HM01",
            "FLY": "HM02",
            "SURF": "HM03",
            "STRENGTH": "HM04",
            "FLASH": "HM05",
        }

        hm_id = hm_map.get(hm_move.upper())
        if not hm_id:
            return AgentResult(
                success=False,
                action_taken="use_hm_in_field",
                error=f"Unknown HM move: {hm_move}",
            )

        # Check if we have the HM usable
        if hm_move.upper() not in [h.upper() for h in state.hms_usable]:
            return AgentResult(
                success=False,
                action_taken="use_hm_in_field",
                error=f"Cannot use {hm_move}: not usable (need badge and taught Pokemon)",
            )

        emulator = self._get_emulator()
        if emulator is None:
            return AgentResult(
                success=True,
                action_taken="use_hm_in_field",
                result_data={
                    "hm_move": hm_move,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        try:
            # Face target direction if needed
            if target_direction in ["UP", "DOWN", "LEFT", "RIGHT"]:
                emulator.press_button(target_direction.lower())
                emulator.tick(8)

            # Open start menu
            emulator.press_button("start")
            emulator.tick(20)

            # Navigate to Pokemon
            emulator.press_button("a")  # POKEMON
            emulator.tick(15)

            # Would need to find HM user and select the move
            # Simplified: select first Pokemon
            emulator.press_button("a")
            emulator.tick(10)

            # Find and select the HM move
            # (Would need actual menu navigation)
            emulator.press_button("a")
            emulator.tick(30)

            if hm_move.upper() == "FLY" and fly_destination:
                # Select destination from town list
                emulator.tick(60)  # Wait for map

            # Wait for animation
            emulator.tick(60)

            return AgentResult(
                success=True,
                action_taken="use_hm_in_field",
                result_data={
                    "hm_move": hm_move,
                    "target_direction": target_direction,
                    "fly_destination": fly_destination,
                    "executed": True,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="use_hm_in_field",
                error=str(e),
            )
