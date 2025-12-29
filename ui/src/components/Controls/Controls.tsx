/**
 * Controls component - pause/play and speed controls.
 */

import { memo, useState } from "react";
import { useGameStore } from "../../stores/gameStore";
import { useWebSocket } from "../../hooks/useWebSocket";
import styles from "./Controls.module.css";

const SPEEDS = [
  { value: 1, label: "1x" },
  { value: 2, label: "2x" },
  { value: 4, label: "4x" },
  { value: 0, label: "Max" },
];

export const Controls = memo(function Controls() {
  const connected = useGameStore((state) => state.connected);
  const running = useGameStore((state) => state.engine?.running ?? false);
  const paused = useGameStore((state) => state.engine?.paused ?? false);
  const { pause, resume, setSpeed } = useWebSocket();
  const [currentSpeed, setCurrentSpeed] = useState(1);

  const handlePlayPause = () => {
    if (paused) {
      resume();
    } else {
      pause();
    }
  };

  const handleSpeedChange = (speed: number) => {
    setCurrentSpeed(speed);
    setSpeed(speed);
  };

  const handleStart = async () => {
    try {
      await fetch("/api/start", { method: "POST" });
    } catch (e) {
      console.error("Failed to start game:", e);
    }
  };

  return (
    <div className={styles.container}>
      <div className={styles.left}>
        <span
          className={`${styles.connectionDot} ${
            connected ? styles.connected : styles.disconnected
          }`}
        />
        <span className={styles.connectionText}>
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>

      <div className={styles.center}>
        {!running ? (
          <button
            className={`${styles.button} ${styles.startButton}`}
            onClick={handleStart}
            disabled={!connected}
          >
            ▶ Start Game
          </button>
        ) : (
          <button
            className={`${styles.button} ${styles.playPauseButton}`}
            onClick={handlePlayPause}
            disabled={!connected}
          >
            {paused ? "▶ Resume" : "⏸ Pause"}
          </button>
        )}
      </div>

      <div className={styles.right}>
        <span className={styles.speedLabel}>Speed:</span>
        <div className={styles.speedButtons}>
          {SPEEDS.map(({ value, label }) => (
            <button
              key={value}
              className={`${styles.speedButton} ${
                currentSpeed === value ? styles.active : ""
              }`}
              onClick={() => handleSpeedChange(value)}
              disabled={!connected || !running}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});
