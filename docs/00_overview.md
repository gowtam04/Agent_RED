# Pokemon Red AI Agent System

## Architecture Overview

This document describes a multi-agent AI system designed to play and complete Pokemon Red. The system uses four specialized agents coordinated by an Orchestrator, with a shared game state for communication.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR [Sonnet 4.5]                           │
│                                                                              │
│   • Detects current game mode (Overworld/Battle/Menu/Dialogue)              │
│   • Maintains objectives stack (what to do next)                            │
│   • Routes control to appropriate specialist agent                          │
│   • Handles failure recovery and sub-objective creation                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
          ┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
          │   NAVIGATION    │ │   BATTLE    │ │      MENU       │
          │  [Haiku 4.5]    │ │[Sonnet 4.5] │ │   [Haiku 4.5]   │
          │                 │ │ [Opus 4.5]* │ │                 │
          │ • Pathfinding   │ │ • Moves     │ │ • Healing       │
          │ • Movement      │ │ • Switching │ │ • Shopping      │
          │ • Exploration   │ │ • Catching  │ │ • Items/TMs     │
          │ • NPC interact  │ │ • Fleeing   │ │ • Party/PC      │
          └─────────────────┘ └─────────────┘ └─────────────────┘
                    │                │                │
                    │   *Opus 4.5 for Gym Leaders,    │
                    │    Elite Four, Rival, Champion  │
                    └────────────────┼────────────────┘
                                     ▼
                    ┌─────────────────────────────────┐
                    │         SHARED GAME STATE       │
                    │                                 │
                    │  • Location & Position          │
                    │  • Party Pokemon                │
                    │  • Inventory & Money            │
                    │  • Badges & Progress            │
                    │  • Current Objective            │
                    │  • Battle State (when active)   │
                    └─────────────────────────────────┘
```

---

## Agent Specifications

| Document | Agent | Primary Responsibility |
|----------|-------|----------------------|
| [01_orchestrator_agent.md](01_orchestrator_agent.md) | Orchestrator | Game mode detection, objective management, agent routing |
| [02_navigation_agent.md](02_navigation_agent.md) | Navigation | Overworld movement, pathfinding, exploration |
| [03_battle_agent.md](03_battle_agent.md) | Battle | Combat decisions, catching, fleeing |
| [04_menu_agent.md](04_menu_agent.md) | Menu | Inventory, healing, shopping, party management |

---

## Model Configuration

We use three Claude models, selected based on reasoning complexity and call frequency:

### Model Assignment

| Agent | Model | Rationale |
|-------|-------|-----------|
| **Orchestrator** | Sonnet 4.5 | Strategic reasoning, frequent calls |
| **Navigation** | Haiku 4.5 | Procedural, highest frequency, speed critical |
| **Battle (normal)** | Sonnet 4.5 | Complex reasoning, turn-based allows latency |
| **Battle (bosses)** | Opus 4.5 | High-stakes fights justify premium reasoning |
| **Menu** | Haiku 4.5 | Simple procedural operations |

### Model Strings

```python
MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251101"
}
```

### Boss Battles (Opus-tier)

The following battle types trigger Opus 4.5:

| Category | Opponents |
|----------|-----------|
| **Gym Leaders** | Brock, Misty, Lt. Surge, Erika, Koga, Sabrina, Blaine, Giovanni |
| **Rival** | All rival encounters (~7 throughout game) |
| **Elite Four** | Lorelei, Bruno, Agatha, Lance |
| **Champion** | Final rival battle |
| **Escalation** | Any trainer beaten us 2+ times |

### Cost Estimation (Full Playthrough)

```
Estimated API calls for one complete game:

Navigation (Haiku):     ~50,000 calls  →  $
Menu (Haiku):           ~2,000 calls   →  $
Orchestrator (Sonnet):  ~10,000 calls  →  $$
Battle - normal (Sonnet): ~3,000 calls →  $$
Battle - bosses (Opus):   ~200 calls   →  $$$

Total: Approximately $X-XX depending on context length
```

### Model Selection Implementation

```python
class ModelSelector:
    """Centralized model selection for all agents."""
    
    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-5-20250929"
    OPUS = "claude-opus-4-5-20251101"
    
    BOSS_BATTLES = {"GYM_LEADER", "ELITE_FOUR", "CHAMPION", "RIVAL"}
    
    @classmethod
    def for_orchestrator(cls) -> str:
        return cls.SONNET
    
    @classmethod
    def for_navigation(cls) -> str:
        return cls.HAIKU
    
    @classmethod
    def for_menu(cls) -> str:
        return cls.HAIKU
    
    @classmethod
    def for_battle(cls, battle_state: BattleState, loss_history: dict) -> str:
        # Boss battles use Opus
        if battle_state.battle_type in cls.BOSS_BATTLES:
            return cls.OPUS
        
        # Escalate after repeated losses
        trainer_id = getattr(battle_state.enemy_trainer, 'id', None)
        if trainer_id and loss_history.get(trainer_id, 0) >= 2:
            return cls.OPUS
        
        # Default to Sonnet
        return cls.SONNET
```

---

## Game State Flow

```
Game starts
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR: Set initial objective "Defeat Elite Four"        │
│  → Break down into "Get 8 Badges" → "Defeat Brock" first       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  NAVIGATION AGENT: Walk toward Pewter City                      │
│  → Wild encounter triggers!                                     │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  BATTLE AGENT: Fight or flee?                                   │
│  → Weak Pokemon, not needed → RUN                               │
│  → OR: Need XP → FIGHT                                          │
│  → OR: Need this type → CATCH                                   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR: Battle ended, check party health                 │
│  → Party HP < 40% → Sub-objective: HEAL                         │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  NAVIGATION AGENT: Navigate to Pokemon Center                   │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  MENU AGENT: Heal at Pokemon Center                             │
│  → Talk to nurse, confirm healing, wait for jingle              │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR: Heal complete, pop sub-objective                 │
│  → Resume: Navigate to Pewter Gym, defeat Brock                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
   ...continues until Champion defeated...
```

---

## Key Design Decisions

### 1. Shared State vs. Message Passing
**Decision:** Shared GameState object

All agents read from and write to a single GameState object. This simplifies communication and ensures consistency. The Orchestrator is responsible for syncing the state after each agent action.

### 2. Agent Granularity  
**Decision:** 4 agents (expandable)

We consolidated to 4 core agents for simplicity:
- Catching logic → inside Battle Agent
- Team management → inside Menu Agent  
- Resource management → inside Menu Agent

This can be expanded later if complexity warrants it.

### 3. Learning/Memory
**Decision:** Static knowledge bases

We use pre-built databases (Pokemon stats, type charts, maps, trainer data) rather than learned memory. This provides reliable, complete information without the complexity of learning systems.

### 4. HM Management
**Decision:** Hardcoded route requirements

The Orchestrator has a lookup table of which routes require which HMs. When a route is blocked, it creates a sub-objective to obtain/teach the required HM.

---

## Static Knowledge Bases Required

| Database | Purpose | Size Estimate |
|----------|---------|---------------|
| Pokemon Data | Stats, types, evolutions, learnsets | ~151 entries |
| Move Data | Power, accuracy, type, effects | ~165 entries |
| Type Chart | Effectiveness multipliers | 15x15 matrix |
| Map Graph | Connections, warps, requirements | ~150 maps |
| Trainer Data | Location, team, vision range | ~300 trainers |
| Item Data | Effects, prices, locations | ~100 items |
| Shop Inventory | What's sold where | ~15 shops |
| HM Requirements | Route → HM needed | ~20 entries |
| Story Progression | Badges → unlocks → next goal | Linear list |

---

## Implementation Phases

### Phase 1: Basic Loop
- [ ] Implement GameState schema
- [ ] Implement Orchestrator mode detection
- [ ] Implement Navigation Agent (walk + basic pathfinding)
- [ ] Implement Battle Agent (trainer battles only, no catching)
- [ ] Implement Menu Agent (Pokemon Center healing only)
- [ ] **Milestone:** Walk between towns, fight trainers, heal

### Phase 2: Core Gameplay
- [ ] Add wild encounter handling (fight or flee)
- [ ] Add catching logic
- [ ] Add shopping functionality
- [ ] Add item usage (potions, status heals)
- [ ] **Milestone:** Defeat first gym (Brock)

### Phase 3: Full Game
- [ ] Add HM usage (Cut, Surf, etc.)
- [ ] Add PC management
- [ ] Add party optimization
- [ ] Add TM teaching
- [ ] Add all gym strategies
- [ ] **Milestone:** Complete game (defeat Elite Four)

### Phase 4: Optimization (Optional)
- [ ] Add encounter manipulation (for specific catches)
- [ ] Add grinding optimization
- [ ] Add speedrun-style optimizations
- [ ] Add episodic memory for failure recovery

---

## Open Questions

1. **Interface Layer:** How does Claude actually control the game?
   - Emulator API?
   - Frame-by-frame image analysis?
   - Memory reading?

2. **State Reading:** How do we read the GameState from the game?
   - Screen parsing (OCR for text, image recognition for sprites)?
   - Direct memory reading (more reliable)?

3. **Timing:** How do we handle game timing?
   - Wait for animations?
   - Frame-perfect inputs?

4. **Error Recovery:** What happens when the agent gets stuck?
   - Hard reset?
   - Load save state?
   - Human intervention?

---

## Getting Started

1. Read each agent specification in order
2. Implement the GameState schema first
3. Build and test each agent individually
4. Integrate with Orchestrator
5. Test on increasingly complex scenarios

The key insight is that Pokemon Red is highly deterministic and has well-defined states. With comprehensive static knowledge and good decision logic, an AI should be able to complete the game without any learning—just planning and execution.
