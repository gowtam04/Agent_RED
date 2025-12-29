"""Battle agent for Pokemon battles."""

from typing import Any

from src.knowledge import PokemonData, TypeChart
from src.tools import BATTLE_TOOLS

from .base import BaseAgent
from .state import GameState
from .types import AgentResult, AgentType, ModelType

BATTLE_SYSTEM_PROMPT = """You are the Battle agent for a Pokemon Red AI system.

Your responsibilities:
1. Select optimal moves based on type effectiveness
2. Decide when to switch Pokemon
3. Determine whether to catch wild Pokemon
4. Manage items in battle
5. Know when to flee from wild battles

You have access to these tools:
- get_pokemon_data: Look up species data
- calculate_type_effectiveness: Check type matchups
- estimate_damage: Calculate expected damage
- calculate_catch_rate: Estimate catch probability
- evaluate_switch_options: Score party matchups
- get_best_move: Rank available moves
- should_catch_pokemon: Evaluate catch priority
- battle_execute_action: Execute move/switch/item/catch/run
- get_battle_state: Read current battle state

Battle strategy:
1. Always consider type effectiveness first
2. Use STAB (Same Type Attack Bonus) moves when effective
3. Switch if current Pokemon has bad matchup AND healthy alternative exists
4. In trainer battles, preserve team for upcoming fights
5. Catch Pokemon that fill team gaps or counter upcoming gyms

Gen 1 quirks to remember:
- Ghost is bugged: does 0x damage to Psychic (not super effective!)
- Special stat is both Special Attack and Special Defense
- High crit moves (Slash, Razor Leaf) have ~25% crit rate
- Focus Energy is bugged and REDUCES crit rate
"""

BOSS_BATTLE_SYSTEM_PROMPT = """You are the Battle agent in a BOSS BATTLE against a Gym Leader, \
Elite Four, or Champion.

This is a critical battle. Think carefully and strategically.

{base_prompt}

Additional boss battle considerations:
1. This trainer has high-level Pokemon with good movesets
2. They may switch tactically - anticipate this
3. Preserve healthy Pokemon for later in the battle
4. Use items strategically (Full Restore before key Pokemon)
5. Consider stat-boosting moves if you have type advantage
6. The trainer cannot be fled from

Think through each decision carefully. What are the opponent's likely moves? What's the safest
path to victory?
"""


class BattleAgent(BaseAgent):
    """Agent for handling Pokemon battles."""

    AGENT_TYPE: AgentType = "BATTLE"
    DEFAULT_MODEL: ModelType = "sonnet"
    SYSTEM_PROMPT: str = BATTLE_SYSTEM_PROMPT

    def __init__(
        self,
        client: Any | None = None,
        model: ModelType | None = None,
    ):
        super().__init__(client, model)
        self._type_chart = TypeChart()
        self._pokemon_data = PokemonData()
        self._emulator = None

    def _register_tools(self) -> list[dict[str, Any]]:
        """Return battle tool definitions."""
        return BATTLE_TOOLS

    def _get_emulator(self) -> Any:
        """Get emulator instance, returns None if not available.

        Note: EmulatorInterface is not a singleton. This method returns
        the emulator if it was set via set_emulator(), otherwise None.
        """
        return self._emulator

    def set_emulator(self, emulator: Any) -> None:
        """Set the emulator instance for this agent."""
        self._emulator = emulator

    def act(self, state: GameState) -> AgentResult:
        """Take a battle action based on current state."""
        # Check for boss battle escalation
        if state.battle and state.battle.battle_type in {
            "GYM_LEADER",
            "ELITE_FOUR",
            "CHAMPION",
        }:
            self.model = "opus"
            self.SYSTEM_PROMPT = BOSS_BATTLE_SYSTEM_PROMPT.format(
                base_prompt=BATTLE_SYSTEM_PROMPT
            )
        else:
            self.model = self.DEFAULT_MODEL
            self.SYSTEM_PROMPT = BATTLE_SYSTEM_PROMPT

        # Format state for Claude
        state_str = self._format_state_for_prompt(state)

        # Add battle-specific context
        if state.battle:
            state_str += f"\n\nBattle Type: {state.battle.battle_type}"
            state_str += f"\nCan Flee: {state.battle.can_flee}"
            state_str += f"\nCan Catch: {state.battle.can_catch}"
            state_str += f"\nTurn: {state.battle.turn_number}"

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
        """Execute a battle tool."""
        tool_handlers = {
            "get_pokemon_data": self._get_pokemon_data,
            "calculate_type_effectiveness": self._calculate_type_effectiveness,
            "estimate_damage": self._estimate_damage,
            "calculate_catch_rate": self._calculate_catch_rate,
            "evaluate_switch_options": self._evaluate_switch_options,
            "get_best_move": self._get_best_move,
            "should_catch_pokemon": self._should_catch_pokemon,
            "battle_execute_action": self._battle_execute_action,
            "get_battle_state": self._get_battle_state,
        }

        handler = tool_handlers.get(tool_name)
        if handler:
            return handler(tool_input, state)

        return AgentResult(
            success=False,
            action_taken=tool_name,
            error=f"Unknown tool: {tool_name}",
        )

    def _get_pokemon_data(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get Pokemon species data from knowledge base."""
        species = tool_input.get("species")
        dex_number = tool_input.get("dex_number")

        if species:
            pokemon = self._pokemon_data.get(species)
        elif dex_number:
            pokemon = self._pokemon_data.get_by_dex_number(dex_number)
        else:
            return AgentResult(
                success=False,
                action_taken="get_pokemon_data",
                error="Must provide species or dex_number",
            )

        if not pokemon:
            return AgentResult(
                success=False,
                action_taken="get_pokemon_data",
                error=f"Pokemon not found: {species or dex_number}",
            )

        return AgentResult(
            success=True,
            action_taken="get_pokemon_data",
            result_data={
                "species": pokemon.get("name", species),
                "types": pokemon.get("types", []),
                "base_stats": pokemon.get("base_stats", {}),
                "catch_rate": pokemon.get("catch_rate", 45),
                "evolutions": pokemon.get("evolutions", []),
                "learnset": pokemon.get("learnset", []),
                "tm_compatibility": pokemon.get("tm_compatibility", []),
                "hm_compatibility": pokemon.get("hm_compatibility", []),
            },
        )

    def _calculate_type_effectiveness(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Calculate type matchup multiplier."""
        attack_type = tool_input["attack_type"]
        defender_types = tool_input["defender_types"]

        multiplier = self._type_chart.get_effectiveness(attack_type, defender_types)

        # Describe effectiveness
        if multiplier == 0:
            effectiveness = "immune"
        elif multiplier < 1:
            effectiveness = "not_very_effective"
        elif multiplier > 1:
            effectiveness = "super_effective"
        else:
            effectiveness = "normal"

        return AgentResult(
            success=True,
            action_taken="calculate_type_effectiveness",
            result_data={
                "attack_type": attack_type.upper(),
                "defender_types": [t.upper() for t in defender_types],
                "multiplier": multiplier,
                "effectiveness": effectiveness,
            },
        )

    def _estimate_damage(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Estimate damage using Gen 1 formula."""
        attacker = tool_input["attacker"]
        defender = tool_input["defender"]
        move = tool_input["move"]
        attacker_stages = tool_input.get("attacker_stages", {"attack": 0, "special": 0})
        defender_stages = tool_input.get(
            "defender_stages", {"defense": 0, "special": 0}
        )

        # Status moves do no damage
        if move.get("category") == "STATUS" or move.get("power", 0) == 0:
            return AgentResult(
                success=True,
                action_taken="estimate_damage",
                result_data={
                    "min_damage": 0,
                    "max_damage": 0,
                    "average_damage": 0,
                    "can_ko": False,
                    "guaranteed_ko": False,
                    "is_status_move": True,
                },
            )

        level = attacker["level"]
        power = move["power"]

        # Gen 1 stat stage multipliers
        stage_multipliers = {
            -6: 2 / 8,
            -5: 2 / 7,
            -4: 2 / 6,
            -3: 2 / 5,
            -2: 2 / 4,
            -1: 2 / 3,
            0: 2 / 2,
            1: 3 / 2,
            2: 4 / 2,
            3: 5 / 2,
            4: 6 / 2,
            5: 7 / 2,
            6: 8 / 2,
        }

        # Determine stat to use (Physical vs Special)
        if move.get("category") == "PHYSICAL":
            base_atk = attacker["attack"]
            base_def = defender["defense"]
            atk_stage = attacker_stages.get("attack", 0)
            def_stage = defender_stages.get("defense", 0)
        else:
            base_atk = attacker["special"]
            base_def = defender["special"]
            atk_stage = attacker_stages.get("special", 0)
            def_stage = defender_stages.get("special", 0)

        # Apply stat stages
        atk = base_atk * stage_multipliers.get(atk_stage, 1.0)
        dfn = base_def * stage_multipliers.get(def_stage, 1.0)

        # Prevent division by zero
        if dfn == 0:
            dfn = 1

        # Base damage formula: ((2 * Level / 5 + 2) * Power * A/D) / 50 + 2
        base = ((2 * level / 5 + 2) * power * atk / dfn) / 50 + 2

        # Type effectiveness
        move_type = move.get("type", "NORMAL")
        defender_types = defender.get("types", [])
        type_mult = self._type_chart.get_effectiveness(move_type, defender_types)

        # STAB (Same Type Attack Bonus)
        attacker_types = attacker.get("types", [])
        stab = 1.5 if move_type.upper() in [t.upper() for t in attacker_types] else 1.0

        # Random modifier (0.85 to 1.0 in Gen 1)
        min_damage = int(base * type_mult * stab * 0.85)
        max_damage = int(base * type_mult * stab * 1.0)

        # Critical hit damage (2x in Gen 1, ignores stat stages)
        crit_base = ((2 * level / 5 + 2) * power * base_atk / base_def) / 50 + 2
        crit_min = int(crit_base * type_mult * stab * 0.85 * 2)
        crit_max = int(crit_base * type_mult * stab * 1.0 * 2)

        defender_hp = defender["current_hp"]
        can_ko = max_damage >= defender_hp
        guaranteed_ko = min_damage >= defender_hp

        return AgentResult(
            success=True,
            action_taken="estimate_damage",
            result_data={
                "min_damage": min_damage,
                "max_damage": max_damage,
                "average_damage": (min_damage + max_damage) // 2,
                "can_ko": can_ko,
                "guaranteed_ko": guaranteed_ko,
                "crit_damage": {"min": crit_min, "max": crit_max},
                "modifiers_applied": {
                    "type_effectiveness": type_mult,
                    "stab": stab,
                },
            },
        )

    def _calculate_catch_rate(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Calculate catch probability using Gen 1 formula."""
        species = tool_input["species"]
        current_hp = tool_input["current_hp"]
        max_hp = tool_input["max_hp"]
        status = tool_input.get("status")
        ball_type = tool_input["ball_type"]

        # Get species catch rate from knowledge base
        pokemon = self._pokemon_data.get(species)
        if not pokemon:
            return AgentResult(
                success=False,
                action_taken="calculate_catch_rate",
                error=f"Unknown species: {species}",
            )

        base_catch_rate = pokemon.get("catch_rate", 45)

        # Master Ball always catches
        if ball_type == "MASTER_BALL":
            return AgentResult(
                success=True,
                action_taken="calculate_catch_rate",
                result_data={
                    "catch_probability": 1.0,
                    "catch_percent": 100.0,
                    "recommended_action": "catch",
                    "notes": "Master Ball guarantees capture",
                },
            )

        # Ball bonus multipliers (Gen 1 uses different formula)
        ball_bonus = {
            "POKE_BALL": 255,
            "GREAT_BALL": 200,
            "ULTRA_BALL": 150,
            "SAFARI_BALL": 255,
        }
        ball_threshold = ball_bonus.get(ball_type, 255)

        # Status multipliers
        status_bonus: float = 1.0
        if status in ["SLEEP", "FREEZE"]:
            status_bonus = 2.0
        elif status in ["PARALYSIS", "BURN", "POISON"]:
            status_bonus = 1.5

        # Gen 1 catch formula (simplified)
        # The actual formula is complex, this is an approximation
        hp_factor = (3 * max_hp - 2 * current_hp) / (3 * max_hp)
        catch_value = (base_catch_rate * ball_threshold / 255) * hp_factor * status_bonus

        # Probability is catch_value / 255, capped at 1.0
        probability = min(catch_value / 255, 1.0)

        # Determine recommendation
        if probability >= 0.8:
            recommendation = "catch"
        elif probability >= 0.4:
            recommendation = "weaken_or_catch"
        elif probability >= 0.2:
            recommendation = "weaken_first"
        else:
            recommendation = "weaken_significantly"

        return AgentResult(
            success=True,
            action_taken="calculate_catch_rate",
            result_data={
                "catch_probability": round(probability, 3),
                "catch_percent": round(probability * 100, 1),
                "recommended_action": recommendation,
                "base_catch_rate": base_catch_rate,
                "hp_percent": round(current_hp / max_hp * 100, 1),
                "status_applied": status,
            },
        )

    def _evaluate_switch_options(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Score all party Pokemon as potential switches."""
        active = tool_input["active_pokemon"]
        party = tool_input["party"]
        enemy = tool_input["enemy_pokemon"]

        enemy_types = enemy.get("types", [])

        switch_options = []

        for i, pokemon in enumerate(party):
            # Skip fainted Pokemon
            if pokemon.get("current_hp", 0) <= 0:
                switch_options.append(
                    {
                        "index": i,
                        "species": pokemon.get("species"),
                        "score": -100,
                        "reason": "fainted",
                    }
                )
                continue

            # Skip currently active Pokemon
            if pokemon.get("species") == active.get("species") and pokemon.get(
                "current_hp"
            ) == active.get("current_hp"):
                switch_options.append(
                    {
                        "index": i,
                        "species": pokemon.get("species"),
                        "score": -1,
                        "reason": "currently_active",
                    }
                )
                continue

            pokemon_types = pokemon.get("types", [])

            # Calculate defensive matchup (how well this Pokemon resists enemy)
            # We check enemy's likely STAB moves against this Pokemon
            defensive_score = 0
            for enemy_type in enemy_types:
                mult = self._type_chart.get_effectiveness(enemy_type, pokemon_types)
                if mult == 0:
                    defensive_score += 50  # Immunity is great
                elif mult < 1:
                    defensive_score += 20  # Resistance is good
                elif mult > 1:
                    defensive_score -= 30  # Weakness is bad

            # Calculate offensive matchup
            offensive_score = 0
            for pokemon_type in pokemon_types:
                mult = self._type_chart.get_effectiveness(pokemon_type, enemy_types)
                if mult > 1:
                    offensive_score += 30  # Super effective STAB
                elif mult == 0:
                    offensive_score -= 20  # Immune is bad

            # HP factor
            hp_percent = (
                pokemon.get("current_hp", 1) / pokemon.get("max_hp", 1)
            ) * 100
            hp_score = hp_percent / 2  # 0-50 points based on HP

            # Speed factor (faster is generally better)
            speed = pokemon.get("speed", 100)
            speed_score = min(speed / 10, 15)  # Up to 15 points

            total_score = defensive_score + offensive_score + hp_score + speed_score

            switch_options.append(
                {
                    "index": i,
                    "species": pokemon.get("species"),
                    "score": round(total_score, 1),
                    "hp_percent": round(hp_percent, 1),
                    "type_matchup": {
                        "defensive": "good" if defensive_score > 0 else "bad",
                        "offensive": "good" if offensive_score > 0 else "neutral",
                    },
                }
            )

        # Sort by score
        switch_options.sort(key=lambda x: x["score"], reverse=True)

        best_option = next(
            (opt for opt in switch_options if opt["score"] > 0), None
        )

        return AgentResult(
            success=True,
            action_taken="evaluate_switch_options",
            result_data={
                "best_switch": best_option,
                "all_options": switch_options,
                "should_switch": best_option is not None
                and best_option["score"] > 30,
            },
        )

    def _get_best_move(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Score and rank available moves."""
        active = tool_input["active_pokemon"]
        enemy = tool_input["enemy_pokemon"]
        _context = tool_input.get("battle_context", {})

        moves = active.get("moves", [])
        enemy_types = enemy.get("types", [])

        move_scores = []

        for i, move in enumerate(moves):
            # Skip moves with no PP
            pp_current = move.get("pp_current", 0)
            if pp_current == 0:
                move_scores.append(
                    {
                        "index": i,
                        "name": move.get("name", "UNKNOWN"),
                        "score": -1,
                        "reason": "no_pp",
                    }
                )
                continue

            power = move.get("power", 0)

            # Status moves get lower base score
            if power == 0:
                move_scores.append(
                    {
                        "index": i,
                        "name": move.get("name", "UNKNOWN"),
                        "score": 20,
                        "reason": "status_move",
                    }
                )
                continue

            # Calculate expected damage via our damage estimation
            damage_result = self._estimate_damage(
                {
                    "attacker": {
                        "level": active.get("level", 50),
                        "attack": active.get("attack", 100),
                        "special": active.get("special", 100),
                        "types": active.get("types", []),
                    },
                    "defender": {
                        "current_hp": int(
                            enemy.get("current_hp_percent", 100)
                        ),  # Estimate
                        "max_hp": 100,
                        "defense": 100,  # Estimate
                        "special": 100,  # Estimate
                        "types": enemy_types,
                    },
                    "move": move,
                },
                state,
            )

            avg_damage = damage_result.result_data.get("average_damage", 0)
            type_mult = damage_result.result_data.get("modifiers_applied", {}).get(
                "type_effectiveness", 1.0
            )

            # Score based on damage and accuracy
            accuracy = move.get("accuracy", 100) / 100
            score = avg_damage * accuracy

            # Bonus for super effective
            if type_mult > 1:
                score *= 1.2

            # Penalty for low accuracy
            if accuracy < 0.8:
                score *= 0.8

            # Bonus for high PP remaining
            pp_max = move.get("pp_max", 10)
            if pp_max > 0 and pp_current / pp_max < 0.25:
                score *= 0.9  # Slight penalty for low PP

            move_scores.append(
                {
                    "index": i,
                    "name": move.get("name", "UNKNOWN"),
                    "score": round(score, 1),
                    "avg_damage": avg_damage,
                    "type_mult": type_mult,
                    "accuracy": move.get("accuracy", 100),
                    "pp": f"{pp_current}/{pp_max}",
                }
            )

        # Sort by score
        move_scores.sort(key=lambda x: x["score"], reverse=True)

        best_move = move_scores[0] if move_scores else None

        return AgentResult(
            success=True,
            action_taken="get_best_move",
            result_data={
                "recommended_move": best_move,
                "all_moves": move_scores,
            },
        )

    def _should_catch_pokemon(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Evaluate whether to catch a wild Pokemon."""
        wild = tool_input["wild_pokemon"]
        party = tool_input["current_party"]
        balls = tool_input["available_balls"]
        _objective = tool_input.get("current_objective")
        upcoming_gym = tool_input.get("upcoming_gym")

        wild_types = wild.get("types", [])
        wild_species = wild.get("species", "UNKNOWN")

        # Check if we already have this Pokemon
        party_species = [p.get("species") for p in party]
        already_have = wild_species in party_species

        # Check party type coverage
        party_types: set[str] = set()
        for p in party:
            party_types.update(p.get("types", []))

        new_types = set(wild_types) - party_types
        adds_coverage = len(new_types) > 0

        # Check if useful against upcoming gym
        useful_for_gym = False
        gym_counters = {
            "BROCK": ["WATER", "GRASS", "FIGHTING"],
            "MISTY": ["ELECTRIC", "GRASS"],
            "LT_SURGE": ["GROUND"],
            "ERIKA": ["FIRE", "ICE", "FLYING", "POISON"],
            "KOGA": ["GROUND", "PSYCHIC"],
            "SABRINA": ["BUG", "GHOST"],  # Note: Ghost is bugged in Gen 1
            "BLAINE": ["WATER", "GROUND", "ROCK"],
            "GIOVANNI": ["WATER", "GRASS", "ICE"],
        }
        if upcoming_gym:
            good_types = gym_counters.get(upcoming_gym.upper(), [])
            useful_for_gym = any(t in wild_types for t in good_types)

        # Check ball availability
        total_balls = sum(balls.values())

        # Scoring
        score = 0
        reasons = []

        if already_have:
            score -= 50
            reasons.append("already_have_species")

        if adds_coverage:
            score += 30
            reasons.append(f"adds_type_coverage: {list(new_types)}")

        if useful_for_gym:
            score += 40
            reasons.append(f"counters_upcoming_gym: {upcoming_gym}")

        if len(party) < 6:
            score += 20
            reasons.append("party_not_full")

        if total_balls < 5:
            score -= 20
            reasons.append("low_ball_count")

        # Decision
        should_catch = score > 20 and total_balls > 0

        return AgentResult(
            success=True,
            action_taken="should_catch_pokemon",
            result_data={
                "should_catch": should_catch,
                "score": score,
                "reasons": reasons,
                "wild_pokemon": wild_species,
                "recommendation": "catch" if should_catch else "defeat_or_flee",
            },
        )

    def _battle_execute_action(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Execute a battle action via emulator."""
        action_type = tool_input["action_type"]

        emulator = self._get_emulator()
        if emulator is None:
            # Return mock result for testing
            return AgentResult(
                success=True,
                action_taken="battle_execute_action",
                result_data={
                    "action": action_type,
                    "executed": False,
                    "reason": "emulator_not_available",
                },
            )

        try:
            if action_type == "MOVE":
                move_index = tool_input.get("move_index", 0)
                # Navigate to FIGHT, then select move
                emulator.press_button("a")  # Select FIGHT
                emulator.tick(10)
                # Navigate to move index
                for _ in range(move_index):
                    emulator.press_button("down")
                    emulator.tick(5)
                emulator.press_button("a")  # Select move
                emulator.tick(30)

            elif action_type == "SWITCH":
                switch_to = tool_input.get("switch_to_index", 0)
                # Navigate to POKEMON
                emulator.press_button("down")
                emulator.tick(5)
                emulator.press_button("a")
                emulator.tick(10)
                # Select Pokemon
                for _ in range(switch_to):
                    emulator.press_button("down")
                    emulator.tick(5)
                emulator.press_button("a")
                emulator.tick(10)
                emulator.press_button("a")  # Confirm switch
                emulator.tick(30)

            elif action_type == "ITEM":
                _item_name = tool_input.get("item", "POTION")
                # Navigate to BAG
                emulator.press_button("right")
                emulator.tick(5)
                emulator.press_button("a")
                emulator.tick(20)
                # Item selection would need inventory navigation
                # Simplified: just press A
                emulator.press_button("a")
                emulator.tick(30)

            elif action_type == "CATCH":
                _ball_type = tool_input.get("ball_type", "POKE_BALL")
                # Navigate to BAG
                emulator.press_button("right")
                emulator.tick(5)
                emulator.press_button("a")
                emulator.tick(20)
                # Select ball (would need proper navigation)
                emulator.press_button("a")
                emulator.tick(120)  # Wait for catch animation

            elif action_type == "RUN":
                # Navigate to RUN
                emulator.press_button("right")
                emulator.tick(5)
                emulator.press_button("down")
                emulator.tick(5)
                emulator.press_button("a")
                emulator.tick(30)

            return AgentResult(
                success=True,
                action_taken="battle_execute_action",
                result_data={
                    "action": action_type,
                    "executed": True,
                    "details": tool_input,
                },
            )

        except Exception as e:
            return AgentResult(
                success=False,
                action_taken="battle_execute_action",
                error=f"Failed to execute action: {str(e)}",
            )

    def _get_battle_state(
        self, tool_input: dict[str, Any], state: GameState
    ) -> AgentResult:
        """Get current battle state."""
        if not state.battle:
            return AgentResult(
                success=False,
                action_taken="get_battle_state",
                error="Not currently in battle",
            )

        battle = state.battle
        our_pokemon = battle.our_pokemon
        enemy_pokemon = battle.enemy_pokemon

        result: dict[str, Any] = {
            "battle_type": battle.battle_type,
            "turn": battle.turn_number,
            "can_flee": battle.can_flee,
            "can_catch": battle.can_catch,
            "our_pokemon": {
                "species": our_pokemon.species,
                "level": our_pokemon.level,
                "hp": f"{our_pokemon.current_hp}/{our_pokemon.max_hp}",
                "hp_percent": round(
                    our_pokemon.current_hp / our_pokemon.max_hp * 100, 1
                ),
                "types": our_pokemon.types,
                "status": our_pokemon.status,
            },
            "enemy_pokemon": {
                "species": enemy_pokemon.species,
                "level": enemy_pokemon.level,
                "hp_percent": round(
                    enemy_pokemon.current_hp / enemy_pokemon.max_hp * 100, 1
                ),
                "types": enemy_pokemon.types,
                "status": enemy_pokemon.status,
            },
            "stat_stages": {
                "our": battle.our_stat_stages,
                "enemy": battle.enemy_stat_stages,
            },
        }

        # Include move details if requested
        include_moves = tool_input.get("include_move_details", True)
        if include_moves and our_pokemon.moves:
            result["our_pokemon"]["moves"] = [
                {
                    "name": m.name,
                    "type": m.type,
                    "power": m.power,
                    "accuracy": m.accuracy,
                    "pp": f"{m.pp_current}/{m.pp_max}",
                }
                for m in our_pokemon.moves
            ]

        if battle.enemy_trainer:
            result["enemy_trainer"] = battle.enemy_trainer
            result["enemy_remaining"] = battle.enemy_remaining

        return AgentResult(
            success=True,
            action_taken="get_battle_state",
            result_data=result,
        )
