"""Agent registry for routing and instantiation."""

import anthropic

from .base import BaseAgent
from .state import GameState
from .types import AgentType, GameMode


class AgentRegistry:
    """Registry for managing agent instances and routing."""

    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic()
        self._agents: dict[AgentType, BaseAgent] = {}

    def get_agent(self, agent_type: AgentType) -> BaseAgent:
        """Get or create an agent instance."""
        if agent_type not in self._agents:
            self._agents[agent_type] = self._create_agent(agent_type)
        return self._agents[agent_type]

    def _create_agent(self, agent_type: AgentType) -> BaseAgent:
        """Create a new agent instance."""
        # Import here to avoid circular imports
        from .battle import BattleAgent
        from .menu import MenuAgent
        from .navigation import NavigationAgent
        from .orchestrator import OrchestratorAgent

        agent_classes: dict[AgentType, type[BaseAgent]] = {
            "ORCHESTRATOR": OrchestratorAgent,
            "NAVIGATION": NavigationAgent,
            "BATTLE": BattleAgent,
            "MENU": MenuAgent,
        }

        agent_class = agent_classes.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}")

        return agent_class(client=self.client)

    def route_by_mode(self, mode: GameMode) -> AgentType:
        """Determine which agent should handle the current mode."""
        mode_routing: dict[GameMode, AgentType] = {
            "OVERWORLD": "NAVIGATION",
            "BATTLE": "BATTLE",
            "MENU": "MENU",
            "DIALOGUE": "MENU",
        }
        return mode_routing[mode]

    def should_escalate_to_opus(self, state: GameState) -> bool:
        """Check if we should use Opus for the current battle."""
        if not state.battle:
            return False

        boss_types = {"GYM_LEADER", "ELITE_FOUR", "CHAMPION"}
        return state.battle.battle_type in boss_types
