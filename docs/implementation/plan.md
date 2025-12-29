# Implementation Plan

## Overview

Transform the Pokemon Red AI from a single-agent MVP to a multi-agent system with specialized agents for different game modes.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                         │
│                      [Sonnet]                           │
│  - Detects game mode                                    │
│  - Manages objective stack                              │
│  - Routes to specialist agents                          │
└─────────────────────────────────────────────────────────┘
           │              │              │
           ▼              ▼              ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │NAVIGATION│   │  BATTLE  │   │   MENU   │
    │ [Haiku]  │   │[Sonnet/  │   │ [Haiku]  │
    │          │   │  Opus]   │   │          │
    └──────────┘   └──────────┘   └──────────┘
```

## Phases

### Phase 1: Knowledge Base Foundation
**Status:** ✅ Completed
**Document:** [phase1_knowledge_base.md](phase1_knowledge_base.md)

Extract game data from pret/pokered repository:
- Type chart (15x15 effectiveness matrix)
- Pokemon data (151 species)
- Move data (165 moves)
- Map data (~150 maps)
- Trainer data (391 trainers)
- Items, shops, wild encounters
- HM requirements and story progression

### Phase 2: Agent Framework
**Status:** ✅ Completed
**Document:** [phase2_agent_framework.md](phase2_agent_framework.md)

Build the multi-agent infrastructure:
- Shared types and enums
- GameState with objective stack
- BaseAgent abstract class
- AgentRegistry for routing
- Tool definitions (38 tools)

### Phase 3: Agent Implementation
**Status:** ✅ Completed
**Document:** [phase3_agents.md](phase3_agents.md)

Implement all 4 specialized agents:
- OrchestratorAgent (7 tools)
- NavigationAgent (8 tools, `find_path` stubbed for Phase 4)
- BattleAgent (9 tools, Opus for bosses)
- MenuAgent (14 tools)

### Phase 4: Pathfinding
**Status:** ✅ Completed
**Document:** [phase4_pathfinding.md](phase4_pathfinding.md)

A* pathfinding system:
- Core A* algorithm (`src/pathfinding/astar.py`)
- Tile weights and grass avoidance (`src/pathfinding/tiles.py`)
- Trainer vision cones (`src/pathfinding/trainer_vision.py`)
- Cross-map routing (`src/pathfinding/cross_map.py`)
- Map data extraction with collision data (`scripts/extract_collision.py`)

### Phase 5: Integration
**Status:** Not Started
**Assignee:** TBD
**Document:** [phase5_integration.md](phase5_integration.md)

Connect all components:
- Update game loop
- Enhance state reader
- Error recovery
- Integration tests

---

## Timeline

```
Week 1: Phase 1 + Phase 2 (parallel)
Week 2: Phase 3 + Phase 4 (parallel)
Week 3: Phase 5 + Testing
```

## Dependencies

```
Phase 1 ──────┬──────> Phase 3 ────┐
              │                    │
Phase 2 ──────┘                    ├──> Phase 5
                                   │
Phase 4 ──────────────────────────┘
```

## Success Metrics

- [ ] Agent can navigate from Pallet Town to Viridian City
- [ ] Agent makes smart battle decisions (type effectiveness)
- [ ] Agent heals when party HP is low
- [ ] Agent defeats Brock (first gym leader)
- [ ] Agent can complete the game (stretch goal)

---

## Notes

- Each phase is designed to be completed by a separate Claude Code agent
- Phase documents contain detailed requirements and success criteria
- All tool schemas are defined in docs/05_tool_schemas.md
- System prompts are in docs/pokemon_red_agent_prompts.md
