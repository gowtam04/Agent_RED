/**
 * GameScreen component - displays the live game screen.
 */

import { memo } from "react";
import { useGameStore } from "../../stores/gameStore";
import styles from "./GameScreen.module.css";

export const GameScreen = memo(function GameScreen() {
  const screen = useGameStore((state) => state.screen);
  const connected = useGameStore((state) => state.connected);
  const game = useGameStore((state) => state.game);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>Game Screen</span>
        {game && (
          <span className={styles.location}>
            {game.position.map_name} ({game.position.x}, {game.position.y})
          </span>
        )}
      </div>
      <div className={styles.screenWrapper}>
        {screen ? (
          <img
            src={`data:image/png;base64,${screen}`}
            alt="Game Screen"
            className={styles.screen}
          />
        ) : (
          <div className={styles.placeholder}>
            {connected ? (
              <>
                <div className={styles.spinner} />
                <span>Waiting for game...</span>
              </>
            ) : (
              <>
                <span className={styles.disconnected}>●</span>
                <span>Disconnected</span>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
});
