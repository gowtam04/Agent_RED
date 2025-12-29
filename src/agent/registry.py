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
        # These will be implemented in Phase 3
        # from .orchestrator import OrchestratorAgent
        # from .navigation import NavigationAgent
        # from .battle import BattleAgent
        # from .menu import MenuAgent

        # agent_classes = {
        #     "ORCHESTRATOR": OrchestratorAgent,
        #     "NAVIGATION": NavigationAgent,
        #     "BATTLE": BattleAgent,
        #     "MENU": MenuAgent,
        # }
        # return agent_classes[agent_type](client=self.client)

        # Phase 2: Framework only - agents will be implemented in Phase 3
        raise NotImplementedError(
            f"Agent '{agent_type}' not yet implemented. "
            "Specialized agents will be added in Phase 3."
        )

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
