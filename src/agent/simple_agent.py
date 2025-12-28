"""Simple Claude agent for playing Pokemon Red."""

import json
from typing import Any, Optional

import structlog
from anthropic import Anthropic

from ..emulator.interface import Button
from ..emulator.state_reader import GameMode, GameState

logger = structlog.get_logger()


class SimpleAgent:
    """
    A simple Claude-powered agent that can play Pokemon Red.

    This is an MVP agent that uses tool calling to interact with the game.
    It makes decisions based on the current game state.
    """

    SYSTEM_PROMPT = """You are an AI playing Pokemon Red on a Game Boy emulator. Your goal is to explore the world, catch Pokemon, battle trainers, and progress through the game.

## Your Capabilities
You can control the game using the available tools:
- press_button: Press a single button (A, B, UP, DOWN, LEFT, RIGHT, START, SELECT)
- move_direction: Move in a direction for one or more tiles
- wait: Wait for animations or events to complete

## Game Modes
The game has different modes that require different actions:
- OVERWORLD: You're walking around. Use move_direction to explore, press A to interact.
- BATTLE: You're in a Pokemon battle. Use press_button to navigate menus and select moves.
- MENU: You're in a menu. Use UP/DOWN to navigate, A to select, B to go back.
- DIALOGUE: Someone is talking. Press A or B to advance text.

## Tips
- In OVERWORLD mode, try to explore new areas and talk to NPCs
- In BATTLE mode, use your Pokemon's moves to defeat enemies
- If you're in a wild battle and don't want to fight, you can try to run (select RUN option)
- Always be aware of your Pokemon's HP - heal at Pokemon Centers when low
- The A button confirms/interacts, B button cancels/goes back

## Important
- Take one action at a time and observe the results
- Be patient - some animations take time
- If stuck, try pressing B to back out of menus
- The game starts at the title screen - press START to begin

Now, based on the current game state provided, decide what action to take next."""

    TOOLS = [
        {
            "name": "press_button",
            "description": "Press a single game button. Use this for menu navigation, confirming actions, or interacting with the world.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "button": {
                        "type": "string",
                        "enum": ["A", "B", "UP", "DOWN", "LEFT", "RIGHT", "START", "SELECT"],
                        "description": "The button to press",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why you're pressing this button",
                    },
                },
                "required": ["button", "reason"],
            },
        },
        {
            "name": "move_direction",
            "description": "Move the player character in a direction. Use this in OVERWORLD mode to walk around.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["UP", "DOWN", "LEFT", "RIGHT"],
                        "description": "Direction to move",
                    },
                    "tiles": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 5,
                        "default": 1,
                        "description": "Number of tiles to move (1-5)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why you're moving this way",
                    },
                },
                "required": ["direction", "reason"],
            },
        },
        {
            "name": "wait",
            "description": "Wait for some time without pressing anything. Use this when waiting for animations, text, or screen transitions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "seconds": {
                        "type": "number",
                        "minimum": 0.1,
                        "maximum": 5.0,
                        "default": 1.0,
                        "description": "How long to wait in seconds",
                    },
                    "reason": {
                        "type": "string",
                        "description": "What you're waiting for",
                    },
                },
                "required": ["reason"],
            },
        },
    ]

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 1024,
    ):
        """
        Initialize the agent.

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens for response
        """
        self._client = Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self._conversation_history: list[dict] = []
        self._action_count = 0

    def get_action(self, game_state: GameState) -> dict[str, Any]:
        """
        Get the next action to take based on the current game state.

        Args:
            game_state: Current state of the game

        Returns:
            Action dictionary with 'type' and action-specific parameters
        """
        # Format the game state for Claude
        state_message = self._format_game_state(game_state)

        # For MVP, use single-turn requests (no conversation history)
        # This avoids tool_use_id mismatch issues and keeps context simple
        messages = [{"role": "user", "content": state_message}]

        # Call Claude
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=self.SYSTEM_PROMPT,
                tools=self.TOOLS,
                messages=messages,
            )
        except Exception as e:
            logger.error("Claude API error", error=str(e))
            # Return a safe default action
            return {
                "type": "wait",
                "seconds": 1.0,
                "reason": f"API error: {e}",
            }

        # Process the response
        action = self._process_response(response)
        self._action_count += 1

        return action

    def _format_game_state(self, state: GameState) -> str:
        """Format the game state as a message for Claude."""
        lines = [
            "=== CURRENT GAME STATE ===",
            f"Frame: {state.frame_count}",
            f"Mode: {state.mode.name}",
            f"Position: Map {state.position.map_id} at ({state.position.x}, {state.position.y}) facing {state.position.facing}",
        ]

        # Party info
        if state.party:
            lines.append(f"\nParty ({state.party_count} Pokemon):")
            for i, p in enumerate(state.party):
                hp_bar = self._make_hp_bar(p.current_hp, p.max_hp)
                status = f" [{p.status}]" if p.status else ""
                lines.append(f"  {i+1}. {p.species_name} Lv.{p.level} {hp_bar}{status}")
        else:
            lines.append("\nParty: Empty (might be at title screen)")

        # Battle info
        if state.battle:
            lines.append(f"\n** BATTLE: {state.battle.battle_type} **")
            lines.append(
                f"Enemy: {state.battle.enemy_species_name} Lv.{state.battle.enemy_level}"
            )
            lines.append(f"Enemy HP: ~{state.battle.enemy_hp_percent:.0f}%")

        # Progress
        lines.append(f"\nBadges: {', '.join(state.badges) if state.badges else 'None'}")
        lines.append(f"Money: ${state.money:,}")

        lines.append("\n=== WHAT IS YOUR NEXT ACTION? ===")

        return "\n".join(lines)

    def _make_hp_bar(self, current: int, max_hp: int, width: int = 10) -> str:
        """Create a text-based HP bar."""
        if max_hp == 0:
            return "[??????????]"
        ratio = current / max_hp
        filled = int(ratio * width)
        return f"[{'█' * filled}{'░' * (width - filled)}] {current}/{max_hp}"

    def _process_response(self, response) -> dict[str, Any]:
        """Process Claude's response and extract the action."""
        # Look for tool use in the response
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                logger.info(
                    "Agent action",
                    tool=tool_name,
                    input=tool_input,
                    reason=tool_input.get("reason", ""),
                )

                return {"type": tool_name, **tool_input}

        # If no tool use, check for text and try to interpret
        for block in response.content:
            if block.type == "text":
                logger.warning("Agent returned text instead of tool", text=block.text[:100])

        # Default to waiting
        return {"type": "wait", "seconds": 0.5, "reason": "No clear action from model"}

    def reset_conversation(self) -> None:
        """Clear the conversation history."""
        self._conversation_history = []

    @property
    def action_count(self) -> int:
        """Get the number of actions taken."""
        return self._action_count
