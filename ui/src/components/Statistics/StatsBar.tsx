/**
 * StatsBar component - displays game statistics.
 */

import { memo } from "react";
import { useGameStore } from "../../stores/gameStore";
import styles from "./StatsBar.module.css";

export const StatsBar = memo(function StatsBar() {
  const engine = useGameStore((state) => state.engine);
  const game = useGameStore((state) => state.game);

  const uptime = engine?.uptime_seconds ?? 0;
  const hours = Math.floor(uptime / 3600);
  const minutes = Math.floor((uptime % 3600) / 60);
  const seconds = Math.floor(uptime % 60);
  const formattedUptime = `${hours.toString().padStart(2, "0")}:${minutes
    .toString()
    .padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;

  const badges = game?.badges ?? [];

  return (
    <div className={styles.container}>
      <div className={styles.stat}>
        <span className={styles.label}>Frames</span>
        <span className={styles.value}>
          {(engine?.total_frames ?? 0).toLocaleString()}
        </span>
      </div>

      <div className={styles.divider} />

      <div className={styles.stat}>
        <span className={styles.label}>API Calls</span>
        <span className={styles.value}>
          {(engine?.api_calls ?? 0).toLocaleString()}
        </span>
      </div>

      <div className={styles.divider} />

      <div className={styles.stat}>
        <span className={styles.label}>Uptime</span>
        <span className={styles.value}>{formattedUptime}</span>
      </div>

      <div className={styles.divider} />

      <div className={styles.stat}>
        <span className={styles.label}>Badges</span>
        <span className={styles.value}>{badges.length}/8</span>
      </div>

      <div className={styles.divider} />

      <div className={styles.stat}>
        <span className={styles.label}>Money</span>
        <span className={styles.value}>
          ${(game?.money ?? 0).toLocaleString()}
        </span>
      </div>

      <div className={styles.divider} />

      <div className={styles.stat}>
        <span className={styles.label}>Mode</span>
        <span className={`${styles.value} ${styles.mode}`}>
          {game?.mode ?? "—"}
        </span>
      </div>
    </div>
  );
});
