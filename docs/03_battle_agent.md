# Battle Agent

## Model Configuration

| Battle Type | Model | Reasoning |
|-------------|-------|-----------|
| Wild encounters | `claude-sonnet-4-5-20250929` | Simple fight/catch/flee decisions |
| Trainer battles | `claude-sonnet-4-5-20250929` | Standard combat reasoning |
| **Gym Leaders** | `claude-opus-4-5-20251101` | High-stakes, complex team strategy |
| **Rival battles** | `claude-opus-4-5-20251101` | Adaptive opponent, critical fights |
| **Elite Four** | `claude-opus-4-5-20251101` | End-game, no healing between fights |
| **Champion** | `claude-opus-4-5-20251101` | Final boss, must win |
| Repeat losses (2+) | `claude-opus-4-5-20251101` | Need deeper analysis |

### Model Selection Logic

```python
def get_battle_model(battle_state: BattleState) -> str:
    """Select the appropriate model based on battle importance."""
    
    OPUS = "claude-opus-4-5-20251101"
    SONNET = "claude-sonnet-4-5-20250929"
    
    # Boss battles always use Opus
    boss_battles = {
        "GYM_LEADER", "ELITE_FOUR", "CHAMPION", "RIVAL"
    }
    if battle_state.battle_type in boss_battles:
        return OPUS
    
    # Escalate to Opus after repeated failures
    trainer_id = battle_state.enemy_trainer.id if battle_state.enemy_trainer else None
    if trainer_id and get_loss_count(trainer_id) >= 2:
        return OPUS
    
    # Default to Sonnet
    return SONNET
```

**Why this split:** Turn-based combat is forgiving on latency, so Sonnet's ~1-2 second response is fine for normal battles. Boss battles (only ~30 total in the game) justify Opus's superior reasoning for multi-Pokemon team strategy and prediction.

---

## Overview

The Battle Agent handles all Pokemon combat encounters, including wild Pokemon battles, trainer battles, and gym leader/Elite Four battles. It makes decisions about which moves to use, when to switch Pokemon, when to use items, and when to catch or flee from wild Pokemon.

## Responsibilities

1. **Move Selection** - Choose the optimal move each turn
2. **Pokemon Switching** - Decide when and what to switch to
3. **Item Usage** - Use healing items, status cures, or X items strategically
4. **Catch Decisions** - Determine if a wild Pokemon should be caught
5. **Flee Decisions** - Determine if fleeing is the right choice
6. **Battle State Tracking** - Monitor HP, PP, status, and stat stages

---

## Battle State Schema

```python
@dataclass
class BattleState:
    # Battle Type
    battle_type: BattleType  # WILD, TRAINER, GYM_LEADER, ELITE_FOUR
    can_flee: bool           # True for wild, False for trainer
    can_catch: bool          # True for wild only
    
    # Our Side
    active_pokemon: Pokemon
    party: list[Pokemon]
    stat_stages: StatStages  # Attack, Defense, etc. modifiers
    
    # Enemy Side
    enemy_pokemon: Pokemon
    enemy_stat_stages: StatStages
    enemy_trainer: Optional[Trainer]
    enemy_remaining: int     # Pokemon left (if trainer)
    
    # Battle Progress
    turn_number: int
    weather: Optional[str]   # Not in Gen 1, but good to have
    
    # Resource Tracking
    balls_available: dict    # {ball_type: count}
    potions_available: dict  # {potion_type: count}


@dataclass
class Pokemon:
    species: str
    level: int
    current_hp: int
    max_hp: int
    status: Optional[str]   # POISON, BURN, SLEEP, FREEZE, PARALYSIS
    types: list[str]
    moves: list[Move]
    stats: Stats


@dataclass
class Move:
    name: str
    type: str
    category: str           # PHYSICAL, SPECIAL, STATUS
    power: int
    accuracy: int
    pp_current: int
    pp_max: int
    effect: Optional[str]   # POISON, PARALYZE, STAT_DOWN, etc.


@dataclass
class StatStages:
    attack: int     # -6 to +6
    defense: int
    special: int    # Gen 1 has combined Special
    speed: int
    accuracy: int
    evasion: int
```

---

## Tools

### 1. `get_pokemon_data`

Retrieves comprehensive data about any Pokemon species.

**Input:** Pokemon species name or ID

**Output:**
```python
{
    "species": "CHARIZARD",
    "types": ["FIRE", "FLYING"],
    "base_stats": {
        "hp": 78,
        "attack": 84,
        "defense": 78,
        "special": 85,
        "speed": 100
    },
    "evolution": {
        "from": "CHARMELEON",
        "to": None,
        "method": "level_36"
    },
    "learnset": [
        {"move": "SCRATCH", "level": 1},
        {"move": "EMBER", "level": 9},
        {"move": "FLAMETHROWER", "level": 46}
    ],
    "tm_compatibility": ["TM02_RAZOR_WIND", "TM06_TOXIC", ...],
    "catch_rate": 45,
    "exp_yield": 209
}
```

---

### 2. `calculate_type_effectiveness`

Calculates type matchup for an attack.

**Input:**
```python
{
    "attack_type": "WATER",
    "defender_types": ["FIRE", "ROCK"]
}
```

**Output:**
```python
{
    "multiplier": 4.0,  # Super effective x2 for each type
    "description": "Super effective (4x)"
}
```

---

### 3. `estimate_damage`

Estimates damage range for a move.

**Input:**
```python
{
    "attacker": Pokemon,
    "defender": Pokemon,
    "move": Move,
    "attacker_stages": StatStages,
    "defender_stages": StatStages
}
```

**Output:**
```python
{
    "min_damage": 45,
    "max_damage": 53,
    "percent_min": 38.1,    # % of defender's current HP
    "percent_max": 44.9,
    "can_ko": False,        # Can this KO in one hit?
    "turns_to_ko": 3        # Estimated turns to KO
}
```

---

### 4. `calculate_catch_rate`

Calculates probability of catching a Pokemon.

**Input:**
```python
{
    "species": "PIKACHU",
    "current_hp": 12,
    "max_hp": 35,
    "status": "PARALYSIS",
    "ball_type": "GREAT_BALL"
}
```

**Output:**
```python
{
    "catch_probability": 0.47,
    "recommended_action": "THROW_BALL",
    "better_option": {
        "if_hp_lower": {"hp": 5, "probability": 0.68},
        "if_asleep": {"probability": 0.72}
    }
}
```

---

### 5. `evaluate_switch_options`

Analyzes switching options against current enemy.

**Input:** Current battle state

**Output:**
```python
{
    "current_matchup": {
        "pokemon": "PIKACHU",
        "score": -2,  # Negative = bad matchup
        "reason": "Ground type incoming move expected"
    },
    "switch_options": [
        {
            "pokemon": "PIDGEOT",
            "score": 3,
            "reason": "Flying immune to Ground, has strong STAB",
            "risks": ["Low HP (34%)"]
        },
        {
            "pokemon": "VENUSAUR", 
            "score": 1,
            "reason": "Resists Ground, good bulk",
            "risks": ["Slower than enemy"]
        }
    ],
    "recommended": "PIDGEOT"
}
```

---

### 6. `get_best_move`

Determines the optimal move for the current situation.

**Input:** Current battle state

**Output:**
```python
{
    "recommended_move": "THUNDERBOLT",
    "reasoning": "Super effective, high power, no risk",
    "alternatives": [
        {
            "move": "THUNDER",
            "note": "Higher power but 70% accuracy"
        },
        {
            "move": "QUICK_ATTACK",
            "note": "Priority, use if enemy low HP and faster"
        }
    ],
    "avoid": [
        {
            "move": "THUNDER_WAVE",
            "reason": "Enemy already paralyzed"
        }
    ]
}
```

---

### 7. `should_catch_pokemon`

Evaluates if a wild Pokemon is worth catching.

**Input:** Wild Pokemon species, current team composition

**Output:**
```python
{
    "should_catch": True,
    "priority": "HIGH",
    "reasons": [
        "No Electric type on team",
        "Pikachu is strong in current meta",
        "Raichu available via Thunder Stone"
    ],
    "concerns": [
        "Low catch rate (190)",
        "May need multiple balls"
    ],
    "ball_recommendation": "GREAT_BALL",
    "prep_recommendation": "Use THUNDER_WAVE first"
}
```

---

### 8. `battle_execute_action`

Executes a battle action (move, switch, item, or run).

**Input:**
```python
{
    "action": "MOVE",
    "move_index": 1,  # THUNDERBOLT
}
# OR
{
    "action": "SWITCH",
    "pokemon_index": 2  # Switch to party slot 2
}
# OR
{
    "action": "ITEM",
    "item": "SUPER_POTION",
    "target_pokemon": 0  # Active Pokemon
}
# OR
{
    "action": "RUN"
}
# OR
{
    "action": "CATCH",
    "ball_type": "GREAT_BALL"
}
```

**Output:**
```python
{
    "success": True,
    "result": {
        "our_move": {"move": "THUNDERBOLT", "damage": 48, "effect": None},
        "enemy_move": {"move": "TACKLE", "damage": 12, "effect": None},
        "enemy_fainted": True,
        "battle_over": False,
        "next_enemy": {"species": "RATICATE", "level": 24}
    }
}
```

---

## Type Chart (Gen 1)

```python
TYPE_CHART = {
    "NORMAL": {"ROCK": 0.5, "GHOST": 0},
    "FIRE": {"FIRE": 0.5, "WATER": 0.5, "GRASS": 2, "ICE": 2, "BUG": 2, "ROCK": 0.5, "DRAGON": 0.5},
    "WATER": {"FIRE": 2, "WATER": 0.5, "GRASS": 0.5, "GROUND": 2, "ROCK": 2, "DRAGON": 0.5},
    "ELECTRIC": {"WATER": 2, "ELECTRIC": 0.5, "GRASS": 0.5, "GROUND": 0, "FLYING": 2, "DRAGON": 0.5},
    "GRASS": {"FIRE": 0.5, "WATER": 2, "GRASS": 0.5, "POISON": 0.5, "GROUND": 2, "FLYING": 0.5, "BUG": 0.5, "ROCK": 2, "DRAGON": 0.5},
    "ICE": {"WATER": 0.5, "GRASS": 2, "ICE": 0.5, "GROUND": 2, "FLYING": 2, "DRAGON": 2},
    "FIGHTING": {"NORMAL": 2, "ICE": 2, "POISON": 0.5, "FLYING": 0.5, "PSYCHIC": 0.5, "BUG": 0.5, "ROCK": 2, "GHOST": 0},
    "POISON": {"GRASS": 2, "POISON": 0.5, "GROUND": 0.5, "BUG": 2, "ROCK": 0.5, "GHOST": 0.5},
    "GROUND": {"FIRE": 2, "ELECTRIC": 2, "GRASS": 0.5, "POISON": 2, "FLYING": 0, "BUG": 0.5, "ROCK": 2},
    "FLYING": {"ELECTRIC": 0.5, "GRASS": 2, "FIGHTING": 2, "BUG": 2, "ROCK": 0.5},
    "PSYCHIC": {"FIGHTING": 2, "POISON": 2, "PSYCHIC": 0.5},
    "BUG": {"FIRE": 0.5, "GRASS": 2, "FIGHTING": 0.5, "POISON": 2, "FLYING": 0.5, "PSYCHIC": 2, "GHOST": 0.5},
    "ROCK": {"FIRE": 2, "ICE": 2, "FIGHTING": 0.5, "GROUND": 0.5, "FLYING": 2, "BUG": 2},
    "GHOST": {"NORMAL": 0, "GHOST": 2, "PSYCHIC": 0},  # Gen 1 bug: Ghost doesn't affect Psychic
    "DRAGON": {"DRAGON": 2}
}
```

---

## Decision Logic

### Move Selection Algorithm

```python
def select_move(battle_state: BattleState) -> Move:
    active = battle_state.active_pokemon
    enemy = battle_state.enemy_pokemon
    
    move_scores = []
    
    for move in active.moves:
        if move.pp_current == 0:
            continue
        
        score = 0
        
        # Base score from damage
        damage = estimate_damage(active, enemy, move)
        score += damage.percent_max * 10
        
        # Bonus for KO potential
        if damage.can_ko:
            score += 50
        
        # Type effectiveness bonus
        effectiveness = calculate_type_effectiveness(move.type, enemy.types)
        score *= effectiveness.multiplier
        
        # Accuracy penalty
        if move.accuracy < 100:
            score *= (move.accuracy / 100)
        
        # Status move logic
        if move.category == "STATUS":
            score = evaluate_status_move(move, battle_state)
        
        # STAB bonus (Same Type Attack Bonus)
        if move.type in active.types:
            score *= 1.5
        
        move_scores.append((move, score))
    
    # Sort by score, return best
    move_scores.sort(key=lambda x: x[1], reverse=True)
    return move_scores[0][0]


def evaluate_status_move(move: Move, state: BattleState) -> float:
    enemy = state.enemy_pokemon
    
    # Don't use status moves if enemy already has status
    if enemy.status and move.effect in ["POISON", "BURN", "SLEEP", "PARALYZE", "FREEZE"]:
        return 0
    
    # Prioritize status for catching
    if state.battle_type == BattleType.WILD and should_catch(enemy):
        if move.effect == "SLEEP":
            return 100  # Sleep is best for catching
        if move.effect == "PARALYZE":
            return 80
    
    # Stat boosting moves
    if move.effect == "ATTACK_UP":
        # Good if we expect a long battle
        if state.enemy_remaining > 2:
            return 60
    
    return 20  # Default low priority for status
```

### Switch Decision Algorithm

```python
def should_switch(battle_state: BattleState) -> tuple[bool, Optional[int]]:
    active = battle_state.active_pokemon
    enemy = battle_state.enemy_pokemon
    
    # Never switch if it's our last Pokemon
    alive_party = [p for p in battle_state.party if p.current_hp > 0]
    if len(alive_party) <= 1:
        return (False, None)
    
    # Calculate current matchup score
    current_score = calculate_matchup_score(active, enemy)
    
    # Check alternatives
    best_switch = None
    best_score = current_score
    
    for i, pokemon in enumerate(battle_state.party):
        if pokemon == active or pokemon.current_hp == 0:
            continue
        
        score = calculate_matchup_score(pokemon, enemy)
        
        # Penalize switching (loses a turn)
        score -= 20
        
        if score > best_score:
            best_score = score
            best_switch = i
    
    # Only switch if significantly better option exists
    if best_switch and (best_score - current_score) > 30:
        return (True, best_switch)
    
    return (False, None)


def calculate_matchup_score(our_pokemon: Pokemon, enemy: Pokemon) -> float:
    score = 0
    
    # Type advantage/disadvantage
    our_best_move = get_best_move_against(our_pokemon, enemy)
    enemy_best_move = get_best_move_against(enemy, our_pokemon)
    
    our_effectiveness = calculate_type_effectiveness(our_best_move.type, enemy.types)
    enemy_effectiveness = calculate_type_effectiveness(enemy_best_move.type, our_pokemon.types)
    
    score += (our_effectiveness.multiplier - 1) * 50
    score -= (enemy_effectiveness.multiplier - 1) * 50
    
    # Speed comparison
    if our_pokemon.stats.speed > enemy.stats.speed:
        score += 20
    
    # HP consideration
    hp_percent = our_pokemon.current_hp / our_pokemon.max_hp
    if hp_percent < 0.25:
        score -= 40  # Risky to stay in with low HP
    
    return score
```

### Catch Decision Algorithm

```python
def decide_catch_action(battle_state: BattleState) -> dict:
    wild = battle_state.enemy_pokemon
    
    # First, should we even try to catch?
    if not should_catch_pokemon(wild.species, game_state.party):
        return {"action": "FIGHT_OR_RUN"}
    
    # Calculate current catch rate
    catch_rate = calculate_catch_rate(
        species=wild.species,
        current_hp=wild.current_hp,
        max_hp=wild.max_hp,
        status=wild.status,
        ball_type=best_available_ball()
    )
    
    # If high catch rate, throw ball
    if catch_rate.catch_probability > 0.5:
        return {
            "action": "CATCH",
            "ball_type": catch_rate.ball_recommendation
        }
    
    # If no status, apply one first
    if wild.status is None:
        status_move = get_status_move(battle_state.active_pokemon)
        if status_move:
            return {"action": "MOVE", "move": status_move}
    
    # If HP too high, weaken it
    if wild.current_hp / wild.max_hp > 0.3:
        weak_move = get_weakening_move(battle_state)
        return {"action": "MOVE", "move": weak_move}
    
    # Otherwise, try to catch
    return {
        "action": "CATCH",
        "ball_type": best_available_ball()
    }
```

---

## Battle Flow

```python
def battle_agent_loop(battle_state: BattleState):
    """Main loop when Battle Agent has control."""
    
    while not battle_state.battle_over:
        # Update state from game
        battle_state = read_battle_state()
        
        # Check if we need to send out a new Pokemon
        if battle_state.active_pokemon.current_hp == 0:
            next_pokemon = choose_next_pokemon(battle_state)
            battle_execute_action({"action": "SWITCH", "pokemon_index": next_pokemon})
            continue
        
        # Wild Pokemon: Catch, fight, or run?
        if battle_state.battle_type == BattleType.WILD:
            decision = decide_catch_action(battle_state)
            
            if decision["action"] == "CATCH":
                result = battle_execute_action(decision)
                if result.caught:
                    return {"status": "CAUGHT", "pokemon": battle_state.enemy_pokemon}
                continue
            
            if decision["action"] == "FIGHT_OR_RUN":
                # Should we run?
                if should_flee(battle_state):
                    result = battle_execute_action({"action": "RUN"})
                    if result.escaped:
                        return {"status": "FLED"}
                    continue
        
        # Check if we should switch
        should_switch, switch_to = should_switch(battle_state)
        if should_switch:
            battle_execute_action({"action": "SWITCH", "pokemon_index": switch_to})
            continue
        
        # Check if we should heal
        if should_use_item(battle_state):
            item = choose_healing_item(battle_state)
            battle_execute_action({"action": "ITEM", "item": item, "target": 0})
            continue
        
        # Select and use best move
        move = select_move(battle_state)
        battle_execute_action({"action": "MOVE", "move_index": move.index})
    
    # Battle ended
    if all_enemy_fainted(battle_state):
        return {"status": "WIN", "exp_gained": battle_state.exp_earned}
    else:
        return {"status": "LOSS"}
```

---

## Special Battle Considerations

### Gym Leader Prep
```python
GYM_RECOMMENDATIONS = {
    "BROCK": {
        "types_needed": ["WATER", "GRASS", "FIGHTING"],
        "level_recommended": 14,
        "key_pokemon": ["ONIX"],
        "strategy": "Use special attacks; Onix has high Defense but low Special"
    },
    "MISTY": {
        "types_needed": ["ELECTRIC", "GRASS"],
        "level_recommended": 21,
        "key_pokemon": ["STARMIE"],
        "strategy": "Starmie is fast and strong; lead with Electric type"
    },
    # ... all gym leaders
}
```

### PP Management
```python
def check_pp_status(pokemon: Pokemon) -> str:
    total_pp = sum(m.pp_current for m in pokemon.moves)
    max_pp = sum(m.pp_max for m in pokemon.moves)
    
    if total_pp == 0:
        return "STRUGGLE_ONLY"  # Must use Struggle
    if total_pp / max_pp < 0.2:
        return "LOW_PP"  # Should heal soon
    return "OK"
```

---

## Integration Points

### ← Orchestrator Provides
- Battle type and context
- Strategic priority (must win vs. can flee)
- Resource constraints (save items for gym?)

### → Returns to Orchestrator
- Win/Loss status
- Resources consumed (items, PP)
- Pokemon caught (if any)
- XP and level-ups

### → May Request from Menu Agent
- Heal mid-battle (rare, mostly for long trainer battles)
- Switch Pokemon order before gym battles
