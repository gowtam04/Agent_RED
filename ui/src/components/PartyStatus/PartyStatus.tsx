/**
 * PartyStatus component - displays Pokemon party with HP bars.
 */

import { memo } from "react";
import { useGameStore } from "../../stores/gameStore";
import type { PokemonStatus } from "../../types/game";
import styles from "./PartyStatus.module.css";

export const PartyStatus = memo(function PartyStatus() {
  const party = useGameStore((state) => state.game?.party ?? []);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>Party Status</span>
        <span className={styles.count}>{party.length}/6</span>
      </div>
      <div className={styles.partyGrid}>
        {party.length === 0 ? (
          <div className={styles.empty}>No Pokemon in party</div>
        ) : (
          party.map((pokemon, index) => (
            <PokemonCard key={index} pokemon={pokemon} slot={index + 1} />
          ))
        )}
        {/* Fill empty slots */}
        {Array.from({ length: 6 - party.length }).map((_, i) => (
          <div key={`empty-${i}`} className={styles.emptySlot}>
            <span className={styles.emptyText}>Empty</span>
          </div>
        ))}
      </div>
    </div>
  );
});

interface PokemonCardProps {
  pokemon: PokemonStatus;
  slot: number;
}

const PokemonCard = memo(function PokemonCard({
  pokemon,
  slot,
}: PokemonCardProps) {
  return (
    <div className={styles.pokemonCard}>
      <div className={styles.pokemonHeader}>
        <span className={styles.slot}>{slot}</span>
        <span className={styles.species}>{pokemon.species}</span>
        <span className={styles.level}>Lv{pokemon.level}</span>
      </div>
      <HPBar current={pokemon.hp} max={pokemon.max_hp} />
      <div className={styles.pokemonFooter}>
        <span className={styles.hpText}>
          {pokemon.hp}/{pokemon.max_hp}
        </span>
        {pokemon.status && (
          <span className={styles.status}>{pokemon.status}</span>
        )}
      </div>
    </div>
  );
});

interface HPBarProps {
  current: number;
  max: number;
}

function HPBar({ current, max }: HPBarProps) {
  const percentage = Math.max(0, Math.min(100, (current / max) * 100));

  let colorClass = styles.hpHigh;
  if (percentage <= 20) {
    colorClass = styles.hpLow;
  } else if (percentage <= 50) {
    colorClass = styles.hpMedium;
  }

  return (
    <div className={styles.hpBar}>
      <div
        className={`${styles.hpFill} ${colorClass}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}
