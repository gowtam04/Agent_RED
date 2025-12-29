"""Base agent class with common functionality."""

from abc import ABC, abstractmethod
from typing import Any, cast

import anthropic

from .state import GameState
from .types import AgentResult, AgentType, ModelType


class BaseAgent(ABC):
    """Base class for all specialized agents."""

    # Override in subclasses
    AGENT_TYPE: AgentType = "ORCHESTRATOR"
    DEFAULT_MODEL: ModelType = "sonnet"
    SYSTEM_PROMPT: str = ""

    def __init__(
        self,
        client: anthropic.Anthropic | None = None,
        model: ModelType | None = None,
    ):
        self.client = client or anthropic.Anthropic()
        self.model = model or self.DEFAULT_MODEL
        self.tools = self._register_tools()
        self.conversation_history: list[dict[str, Any]] = []

    @abstractmethod
    def _register_tools(self) -> list[dict[str, Any]]:
        """Return the tool definitions for this agent."""
        pass

    @abstractmethod
    def act(self, state: GameState) -> AgentResult:
        """Take an action based on the current game state."""
        pass

    def _get_model_id(self) -> str:
        """Convert model type to full model ID."""
        model_map = {
            "haiku": "claude-3-haiku-20240307",
            "sonnet": "claude-sonnet-4-20250514",
            "opus": "claude-opus-4-20250514",
        }
        return model_map[self.model]

    def _call_claude(
        self,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> anthropic.types.Message:
        """Make an API call to Claude."""
        return self.client.messages.create(
            model=self._get_model_id(),
            max_tokens=max_tokens,
            system=system or self.SYSTEM_PROMPT,
            tools=self.tools,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )

    def _format_state_for_prompt(self, state: GameState) -> str:
        """Format the game state as a human-readable string for the prompt."""
        lines = [
            "=== GAME STATE ===",
            f"Mode: {state.mode}",
            f"Location: {state.position.map_id} ({state.position.x}, {state.position.y})",
            f"Facing: {state.position.facing}",
            "",
            f"=== PARTY ({len(state.party)} Pokemon) ===",
        ]

        for i, pokemon in enumerate(state.party):
            status = f" [{pokemon.status}]" if pokemon.status else ""
            hp_pct = pokemon.current_hp / pokemon.max_hp * 100
            lines.append(
                f"{i+1}. {pokemon.species} Lv{pokemon.level} "
                f"HP: {pokemon.current_hp}/{pokemon.max_hp} ({hp_pct:.0f}%){status}"
            )

        lines.extend(
            [
                "",
                "=== PROGRESS ===",
                f"Badges: {', '.join(state.badges) if state.badges else 'None'}",
                f"Money: ${state.money}",
                f"HMs usable: {', '.join(state.hms_usable) if state.hms_usable else 'None'}",
            ]
        )

        if state.current_objective:
            lines.extend(
                [
                    "",
                    "=== CURRENT OBJECTIVE ===",
                    f"Type: {state.current_objective.type}",
                    f"Target: {state.current_objective.target}",
                ]
            )

        if state.battle:
            enemy = state.battle.enemy_pokemon
            enemy_hp_pct = enemy.current_hp / enemy.max_hp * 100
            lines.extend(
                [
                    "",
                    "=== BATTLE ===",
                    f"Type: {state.battle.battle_type}",
                    f"Enemy: {enemy.species} Lv{enemy.level}",
                    f"Enemy HP: ~{enemy_hp_pct:.0f}%",
                ]
            )

        return "\n".join(lines)

    def _process_tool_calls(
        self,
        response: anthropic.types.Message,
        state: GameState,
    ) -> AgentResult:
        """Process tool calls from Claude's response."""
        # First, capture all text blocks as reasoning (Claude's thoughts)
        reasoning_parts: list[str] = []
        for block in response.content:
            if block.type == "text" and block.text.strip():
                reasoning_parts.append(block.text)
        reasoning = "\n".join(reasoning_parts) if reasoning_parts else None

        # Process tool calls
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = cast(dict[str, Any], block.input)

                # Execute the tool and attach reasoning
                result = self._execute_tool(tool_name, tool_input, state)
                result.reasoning = reasoning
                return result

        # No tool call - text-only response
        return AgentResult(
            success=True,
            action_taken="response",
            result_data={"text": reasoning or ""},
            reasoning=reasoning,
        )

    @abstractmethod
    def _execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        state: GameState,
    ) -> AgentResult:
        """Execute a specific tool. Implement in subclass."""
        pass
