# Implementation Phases

This directory contains detailed requirement documents for each phase of the Pokemon Red AI Agent implementation. Each phase is designed to be completed independently by a separate Claude Code agent.

## Phases

| Phase | Document | Description | Dependencies |
|-------|----------|-------------|--------------|
| 1 | [phase1_knowledge_base.md](phase1_knowledge_base.md) | Extract game data from pokered repo | None |
| 2 | [phase2_agent_framework.md](phase2_agent_framework.md) | Build multi-agent infrastructure | None |
| 3 | [phase3_agents.md](phase3_agents.md) | Implement all 4 specialized agents | Phase 1, 2 |
| 4 | [phase4_pathfinding.md](phase4_pathfinding.md) | A* pathfinding system | Phase 1 |
| 5 | [phase5_integration.md](phase5_integration.md) | Connect all components | Phase 1-4 |

## Dependency Graph

```
Phase 1 (Knowledge Base) ─────┬─────> Phase 3 (Agents) ────┐
                              │                            │
Phase 2 (Agent Framework) ────┘                            ├─> Phase 5 (Integration)
                                                           │
Phase 4 (Pathfinding) ────────────────────────────────────┘
```

## Parallel Execution

Phases that can be worked on in parallel:
- **Phase 1** and **Phase 2** have no dependencies and can start immediately
- **Phase 4** only depends on Phase 1 (map data) and can run in parallel with Phase 3
- **Phase 3** requires both Phase 1 and Phase 2
- **Phase 5** requires all other phases

## How to Use

Each phase document contains:
1. **Objective** - What the phase accomplishes
2. **Prerequisites** - What must be complete before starting
3. **Deliverables** - Specific files and code to produce
4. **Success Criteria** - How to verify the phase is complete
5. **Testing** - Unit and integration tests to write

### Starting a Phase

```bash
# Example: Start Phase 1
# Tell Claude Code agent:
"Read /docs/implementation/phase1_knowledge_base.md and implement all deliverables"
```

### Verifying Completion

Each phase has a "Success Criteria" section with checkboxes. The phase is complete when all criteria are met:

```bash
# Run tests for the phase
poetry run pytest tests/test_knowledge/  # Phase 1
poetry run pytest tests/test_agent/      # Phase 2
poetry run pytest tests/test_pathfinding/ # Phase 4
poetry run pytest tests/test_integration/ # Phase 5
```

## Summary by Phase

### Phase 1: Knowledge Base
- Clone `pret/pokered` repository
- Parse ASM files to extract game data
- Generate 10 JSON files (pokemon, moves, types, maps, etc.)
- Create Python accessor classes

### Phase 2: Agent Framework
- Define shared types and enums
- Create `GameState` with objective stack
- Implement `BaseAgent` abstract class
- Build `AgentRegistry` for routing

### Phase 3: Agents
- Implement `OrchestratorAgent` (7 tools)
- Implement `NavigationAgent` (8 tools)
- Implement `BattleAgent` (9 tools) with Opus escalation
- Implement `MenuAgent` (14 tools)

### Phase 4: Pathfinding
- Implement A* algorithm
- Create map graph representation
- Handle tile weights (grass avoidance)
- Build cross-map routing
- Model trainer vision cones

### Phase 5: Integration
- Update game loop with Orchestrator pattern
- Enhance state reader with battle/menu detection
- Add error recovery
- Create integration tests
- Configure CLI entry point

## File Structure After All Phases

```
src/
├── agent/
│   ├── __init__.py
│   ├── base.py
│   ├── orchestrator.py
│   ├── navigation.py
│   ├── battle.py
│   ├── menu.py
│   ├── state.py
│   ├── types.py
│   ├── objective.py
│   └── registry.py
├── knowledge/
│   ├── __init__.py
│   ├── base.py
│   ├── pokemon.py
│   ├── moves.py
│   ├── type_chart.py
│   ├── items.py
│   ├── maps.py
│   ├── trainers.py
│   ├── shops.py
│   ├── wild_encounters.py
│   ├── hm_requirements.py
│   └── story_progression.py
├── pathfinding/
│   ├── __init__.py
│   ├── astar.py
│   ├── graph.py
│   ├── tiles.py
│   ├── cross_map.py
│   └── trainer_vision.py
├── tools/
│   ├── __init__.py
│   └── definitions.py
├── emulator/
│   ├── interface.py
│   └── state_reader.py
├── config.py
├── recovery.py
├── logging_config.py
└── main.py

data/
├── pokemon.json
├── moves.json
├── type_chart.json
├── items.json
├── trainers.json
├── shops.json
├── wild_encounters.json
├── hm_requirements.json
├── story_progression.json
└── maps/
    ├── index.json
    └── [map_id].json

external/
└── pokered/

scripts/
├── extract_pokemon.py
├── extract_moves.py
├── extract_types.py
├── extract_maps.py
├── extract_trainers.py
├── extract_items.py
├── extract_shops.py
├── extract_wild.py
└── extract_all.py

tests/
├── test_knowledge/
├── test_agent/
├── test_pathfinding/
└── test_integration/
```
