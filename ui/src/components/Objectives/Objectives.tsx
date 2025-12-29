/**
 * Objectives component - displays the objective stack.
 */

import { memo } from "react";
import { useGameStore } from "../../stores/gameStore";
import styles from "./Objectives.module.css";

// Objective type icons
const objectiveIcons: Record<string, string> = {
  become_champion: "🏆",
  defeat_gym: "🎯",
  catch_pokemon: "🔴",
  heal: "💊",
  navigate: "📍",
  grind: "⚔️",
  shop: "🛒",
  default: "📋",
};

export const Objectives = memo(function Objectives() {
  const objectives = useGameStore(
    (state) => state.engine?.objective_stack ?? []
  );

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>Objectives</span>
        <span className={styles.count}>{objectives.length}</span>
      </div>
      <div className={styles.objectivesList}>
        {objectives.length === 0 ? (
          <div className={styles.empty}>No active objectives</div>
        ) : (
          objectives.map((objective, index) => (
            <div
              key={index}
              className={`${styles.objective} ${
                index === 0 ? styles.current : ""
              }`}
            >
              <span className={styles.icon}>
                {objectiveIcons[objective.type] || objectiveIcons.default}
              </span>
              <div className={styles.objectiveContent}>
                <span className={styles.objectiveType}>{objective.type}</span>
                <span className={styles.objectiveTarget}>
                  {objective.target}
                </span>
              </div>
              <span className={styles.priority}>P{objective.priority}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
});
