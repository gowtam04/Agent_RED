"""Orchestrator agent for central coordination."""

from typing import Any

from src.knowledge import StoryProgression
from src.tools import ORCHESTRATOR_TOOLS

from .base import BaseAgent
from .objective import create_heal_objective
from .state import GameState
from .types import AgentResult, AgentType, ModelType, Objective

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator agent for a Pokemon Red AI system.

Your responsibilities:
1. Detect the current game mode (OVERWORLD, BATTLE, MENU, DIALOGUE)
2. Manage the objective stack (current goal, sub-goals, prerequisites)
3. Route to the appropriate specialist agent
4. Monitor party health and trigger healing when needed
5. Handle failure recovery

You have access to the following tools:
- detect_game_mode: Identify current game state
- get_current_objective: Get the top objective
- get_next_milestone: Determine next story milestone
- check_requirements: Verify prerequisites are met
- route_to_agent: Select specialist agent
- update_game_state: Sync shared state
- manage_objective_stack: Push/pop objectives

Decision flow:
1. First, detect the game mode
2. Check if party needs healing (HP < 50% or fainted Pokemon)
3. If healing needed, push heal objective and route to appropriate agent
4. Otherwise, get current objective and route based on mode

Always think step by step about what the player should do next to progress.
"""


class OrchestratorAgent(BaseAgent):
    """Agent for central coordination and routing."""

    AGENT_TYPE: AgentType = "ORCHESTRATOR"
    DEFAULT_MODEL: ModelType = "sonnet"
    SYSTEM_PROMPT: str = ORCHESTRATOR_SYSTEM_PROMPT

    def __init__(
        self,
        client: Any | None = None,
        model: ModelType | None = None,
    ):
        super().__init__(client, model)
        self._story_progression = StoryProgression()
        self._state_reader: Any = None

    def _register_tools(self) -> list[dict[str, Any]]:
        """Return orchestrator tool definitions."""
        return ORCHESTRATOR_TOOLS

    def _get_state_reader(self) -> Any:
        """Get state reader instance, returns None if not available."""
        return self._state_reader

    def set_emulator(self, emulator: Any) -> None:
        """Set the emulator instance for this agent."""
        if emulator:
            try:
                from src.emulator.state_reader import StateReader

                self._state_reader = StateReader(emulator)
            except Exception:
                pass

    def act(self, state: GameState) -> AgentResult:
        """Determine next action and route to appropriate agent."""
        # Format state for Claude
        state_str = self._format_state_for_prompt(state)

        # Add orchestrator-specific context
        state_str += "\n\n=== ORCHESTRATION CONTEXT ==="
        state_str += f"\nNeeds Healing: {state.needs_healing}"
        state_str += f"\nParty HP: {state.party_hp_percent:.1f}%"
        state_str += f"\nFainted: {state.fainted_count}"
        state_str += f"\nObjective Stack Depth: {len(state.objective_stack)}"

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
        """Execute an orchestrator tool."""
        tool_handlers = {
            "detect_game_mode": self._detect_game_mode,
            "get_current_objective": self._get_current_objective,
            "get_next_milestone": self._get_next_milestone,
            "check_requirements": self._check_requirements,
            "route_to_agent": self._route_to_agent,
            "update_game_state": self._update_game_state,
            "manage_objective_stack": self._manage_objective_stack,
        }

        handler = tool_handlers.get(tool_name)
        if handler:
            return handler(tool_input, state)

        return AgentResult(
            success=False,
            action_taken=tool_name,
            error=f"Unknown tool: {tool_name}",
        )

    def _detect_game_mode(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Detect current game mode from memory or state."""
        state_reader = self._get_state_reader()

        if state_reader:
            try:
                game_mode = state_reader.get_game_mode()

                # Check for battle submodes
                submode = None
                if game_mode.value == "BATTLE":
                    battle_state = state_reader.get_battle_state()
                    if battle_state:
                        # Determine battle type from memory
                        # 1 = wild, 2 = trainer
                        submode = "WILD"  # Default, would read from memory

                return AgentResult(
                    success=True,
                    action_taken="detect_game_mode",
                    result_data={
                        "mode": game_mode.value,
                        "submode": submode,
                        "source": "memory",
                    },
                )
            except Exception:
                pass

        # Fall back to state
        mode = state.mode
        submode = None

        if mode == "BATTLE" and state.battle:
            submode = state.battle.battle_type

        return AgentResult(
            success=True,
            action_taken="detect_game_mode",
            result_data={
                "mode": mode,
                "submode": submode,
                "source": "cached_state",
            },
        )

    def _get_current_objective(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get current objective from stack."""
        current = state.current_objective

        if not current:
            # No objective set, determine from progress
            badges = tool_input.get("badges", state.badges)
            story_flags = tool_input.get("story_flags", state.story_flags)

            # Get next milestone based on progress
            completed: set[str] = set()
            for badge in badges:
                completed.add(f"gym_{badge.lower()}")
            for flag in story_flags:
                completed.add(flag.lower())

            available = self._story_progression.get_available_milestones(completed)
            milestone = available[0] if available else None

            if milestone:
                return AgentResult(
                    success=True,
                    action_taken="get_current_objective",
                    result_data={
                        "objective": None,
                        "suggested_objective": {
                            "type": milestone.get("type", "progress"),
                            "target": milestone.get("target"),
                            "description": milestone.get("description"),
                        },
                        "needs_objective": True,
                    },
                )

            return AgentResult(
                success=True,
                action_taken="get_current_objective",
                result_data={
                    "objective": None,
                    "needs_objective": True,
                    "suggestion": "Set a new objective",
                },
            )

        return AgentResult(
            success=True,
            action_taken="get_current_objective",
            result_data={
                "objective": {
                    "type": current.type,
                    "target": current.target,
                    "priority": current.priority,
                    "requirements": current.requirements,
                    "completed": current.completed,
                },
                "stack_depth": len(state.objective_stack),
            },
        )

    def _get_next_milestone(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Determine next story milestone."""
        badges = tool_input.get("badges", state.badges)
        story_flags = tool_input.get("story_flags", state.story_flags)
        _hms_obtained = tool_input.get("hms_obtained", state.hms_obtained)
        _hms_usable = tool_input.get("hms_usable", state.hms_usable)

        # Get available milestones based on progress
        # Convert badge list to set of completed milestone IDs
        completed: set[str] = set()
        for badge in badges:
            completed.add(f"gym_{badge.lower()}")
        for flag in story_flags:
            completed.add(flag.lower())

        available = self._story_progression.get_available_milestones(completed)
        milestone = available[0] if available else None

        if not milestone:
            return AgentResult(
                success=True,
                action_taken="get_next_milestone",
                result_data={
                    "milestone": None,
                    "note": "No next milestone found - game may be complete",
                    "badges_obtained": len(badges),
                },
            )

        # Break down into steps
        steps = milestone.get("steps", [])
        if not steps:
            # Generate basic steps
            if milestone.get("type") == "defeat_gym":
                gym = milestone.get("target")
                steps = [
                    f"Navigate to {gym}'s gym",
                    "Defeat gym trainers",
                    f"Defeat {gym}",
                ]
            elif milestone.get("type") == "get_item":
                steps = [
                    f"Navigate to {milestone.get('location', 'location')}",
                    f"Obtain {milestone.get('target')}",
                ]

        return AgentResult(
            success=True,
            action_taken="get_next_milestone",
            result_data={
                "milestone": {
                    "type": milestone.get("type"),
                    "target": milestone.get("target"),
                    "location": milestone.get("location"),
                    "description": milestone.get("description"),
                },
                "steps": steps,
                "prerequisites": milestone.get("prerequisites", []),
                "progress": {
                    "badges": len(badges),
                    "story_flags": len(story_flags),
                },
            },
        )

    def _check_requirements(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Check if requirements are met for an objective."""
        objective_type = tool_input["objective_type"]
        objective_target = tool_input["objective_target"]
        current_state = tool_input.get("current_state", {})

        # Extract state info
        badges = current_state.get("badges", state.badges)
        _hms_obtained = current_state.get("hms_obtained", state.hms_obtained)
        _hms_usable = current_state.get("hms_usable", state.hms_usable)
        _key_items = current_state.get("key_items", state.key_items)
        party_types = current_state.get("party_types", [])

        if not party_types and state.party:
            for pokemon in state.party:
                party_types.extend(pokemon.types)
            party_types = list(set(party_types))

        # Check requirements based on objective type
        missing = []
        suggestions = []

        if objective_type == "navigate":
            # Check HM requirements for route
            # This would use HMRequirements knowledge base
            pass

        elif objective_type == "defeat_gym":
            # Check type advantages (gym_types for reference)
            _gym_types = {
                "BROCK": ["ROCK", "GROUND"],
                "MISTY": ["WATER"],
                "LT_SURGE": ["ELECTRIC"],
                "ERIKA": ["GRASS", "POISON"],
                "KOGA": ["POISON"],
                "SABRINA": ["PSYCHIC"],
                "BLAINE": ["FIRE"],
                "GIOVANNI": ["GROUND", "ROCK"],
            }

            gym_counters = {
                "BROCK": ["WATER", "GRASS", "FIGHTING"],
                "MISTY": ["ELECTRIC", "GRASS"],
                "LT_SURGE": ["GROUND"],
                "ERIKA": ["FIRE", "ICE", "FLYING", "POISON"],
                "KOGA": ["GROUND", "PSYCHIC"],
                "SABRINA": ["BUG"],  # Ghost bugged in Gen 1
                "BLAINE": ["WATER", "GROUND", "ROCK"],
                "GIOVANNI": ["WATER", "GRASS", "ICE"],
            }

            target_upper = objective_target.upper()
            if target_upper in gym_counters:
                good_types = gym_counters[target_upper]
                has_counter = any(t in party_types for t in good_types)
                if not has_counter:
                    suggestions.append(
                        {
                            "type": "catch_pokemon",
                            "reason": f"Get Pokemon with {good_types} type for type advantage",
                        }
                    )

        elif objective_type == "catch_pokemon":
            # Check for Poke Balls
            if "POKE_BALL" not in state.items and "GREAT_BALL" not in state.items:
                missing.append({"type": "item", "need": "Poke Balls"})
                suggestions.append({"type": "shop", "reason": "Buy Poke Balls"})

        elif objective_type == "get_hm":
            # Check prerequisites for HM locations
            pass

        elif objective_type == "teach_hm":
            hm_badges = {
                "CUT": "CASCADE",
                "FLY": "THUNDER",
                "SURF": "SOUL",
                "STRENGTH": "RAINBOW",
                "FLASH": "BOULDER",
            }
            required_badge = hm_badges.get(objective_target.upper())
            if required_badge and required_badge not in [b.upper() for b in badges]:
                missing.append({"type": "badge", "need": required_badge})

        requirements_met = len(missing) == 0

        return AgentResult(
            success=True,
            action_taken="check_requirements",
            result_data={
                "objective_type": objective_type,
                "objective_target": objective_target,
                "requirements_met": requirements_met,
                "missing": missing,
                "suggestions": suggestions,
            },
        )

    def _route_to_agent(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Route to appropriate specialist agent."""
        game_mode = tool_input.get("game_mode", state.mode)
        current_objective = tool_input.get("current_objective")
        game_state_summary = tool_input.get("game_state_summary", {})

        # Check for healing priority
        needs_healing = game_state_summary.get("party_avg_hp_percent", 100) < 50
        needs_healing = needs_healing or game_state_summary.get("fainted_count", 0) > 0
        needs_healing = needs_healing or state.needs_healing

        if needs_healing and game_mode != "BATTLE":
            return AgentResult(
                success=True,
                action_taken="route_to_agent",
                result_data={
                    "agent": "MENU",
                    "reason": "party_needs_healing",
                    "priority": "high",
                },
                new_objectives=[create_heal_objective()],
            )

        # Standard routing
        routing = {
            "OVERWORLD": "NAVIGATION",
            "BATTLE": "BATTLE",
            "MENU": "MENU",
            "DIALOGUE": "MENU",
        }

        agent = routing.get(game_mode, "NAVIGATION")

        # Check for boss battle escalation
        if game_mode == "BATTLE" and state.battle:
            if state.battle.battle_type in {"GYM_LEADER", "ELITE_FOUR", "CHAMPION"}:
                return AgentResult(
                    success=True,
                    action_taken="route_to_agent",
                    result_data={
                        "agent": "BATTLE",
                        "escalate_to_opus": True,
                        "reason": f"boss_battle: {state.battle.battle_type}",
                        "enemy_trainer": state.battle.enemy_trainer,
                    },
                )

        return AgentResult(
            success=True,
            action_taken="route_to_agent",
            result_data={
                "agent": agent,
                "game_mode": game_mode,
                "current_objective": current_objective,
            },
        )

    def _update_game_state(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Update shared game state."""
        updates = tool_input["updates"]
        source = tool_input["source"]

        updated_fields = []

        # Apply updates
        if "current_mode" in updates:
            state.mode = updates["current_mode"]
            updated_fields.append("mode")

        if "current_map" in updates:
            state.position.map_id = updates["current_map"]
            updated_fields.append("position.map_id")

        if "player_position" in updates:
            pos = updates["player_position"]
            if "x" in pos:
                state.position.x = pos["x"]
            if "y" in pos:
                state.position.y = pos["y"]
            updated_fields.append("position")

        if "money" in updates:
            state.money = updates["money"]
            updated_fields.append("money")

        if "badges" in updates:
            state.badges = updates["badges"]
            updated_fields.append("badges")

        if "story_flags" in updates:
            state.story_flags = updates["story_flags"]
            updated_fields.append("story_flags")

        return AgentResult(
            success=True,
            action_taken="update_game_state",
            result_data={
                "updated_fields": updated_fields,
                "source": source,
            },
        )

    def _manage_objective_stack(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Manage the objective stack."""
        operation = tool_input["operation"]
        objective_data = tool_input.get("objective")

        if operation == "push":
            if not objective_data:
                return AgentResult(
                    success=False,
                    action_taken="manage_objective_stack",
                    error="push requires objective data",
                )

            objective = Objective(
                type=objective_data.get("type", "unknown"),
                target=objective_data.get("target", ""),
                priority=objective_data.get("priority", 1),
                requirements=objective_data.get("requirements", []),
            )
            state.push_objective(objective)

            return AgentResult(
                success=True,
                action_taken="manage_objective_stack",
                result_data={
                    "operation": "push",
                    "objective": {
                        "type": objective.type,
                        "target": objective.target,
                    },
                    "stack_depth": len(state.objective_stack),
                },
            )

        elif operation == "pop":
            popped = state.pop_objective()
            if not popped:
                return AgentResult(
                    success=False,
                    action_taken="manage_objective_stack",
                    error="Objective stack is empty",
                )

            return AgentResult(
                success=True,
                action_taken="manage_objective_stack",
                result_data={
                    "operation": "pop",
                    "popped": {
                        "type": popped.type,
                        "target": popped.target,
                        "completed": popped.completed,
                    },
                    "stack_depth": len(state.objective_stack),
                },
            )

        elif operation == "peek":
            current = state.current_objective
            if not current:
                return AgentResult(
                    success=True,
                    action_taken="manage_objective_stack",
                    result_data={
                        "operation": "peek",
                        "current": None,
                        "stack_depth": 0,
                    },
                )

            return AgentResult(
                success=True,
                action_taken="manage_objective_stack",
                result_data={
                    "operation": "peek",
                    "current": {
                        "type": current.type,
                        "target": current.target,
                        "priority": current.priority,
                        "completed": current.completed,
                    },
                    "stack_depth": len(state.objective_stack),
                },
            )

        elif operation == "clear_completed":
            # Remove all completed objectives
            before = len(state.objective_stack)
            state.objective_stack = [
                obj for obj in state.objective_stack if not obj.completed
            ]
            after = len(state.objective_stack)

            return AgentResult(
                success=True,
                action_taken="manage_objective_stack",
                result_data={
                    "operation": "clear_completed",
                    "removed_count": before - after,
                    "stack_depth": after,
                },
            )

        return AgentResult(
            success=False,
            action_taken="manage_objective_stack",
            error=f"Unknown operation: {operation}",
        )
