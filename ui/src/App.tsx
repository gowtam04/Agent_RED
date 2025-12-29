/**
 * Main App component - dashboard layout.
 */

import { AgentThoughts } from "./components/AgentThoughts/AgentThoughts";
import { Controls } from "./components/Controls/Controls";
import { EventLog } from "./components/EventLog/EventLog";
import { GameScreen } from "./components/GameScreen/GameScreen";
import { Objectives } from "./components/Objectives/Objectives";
import { PartyStatus } from "./components/PartyStatus/PartyStatus";
import { StatsBar } from "./components/Statistics/StatsBar";
import { useWebSocket } from "./hooks/useWebSocket";
import styles from "./App.module.css";

function App() {
  // Initialize WebSocket connection
  useWebSocket();

  return (
    <div className={styles.app}>
      {/* Header with controls */}
      <header className={styles.header}>
        <div className={styles.titleSection}>
          <h1 className={styles.title}>Pokemon Red AI Agent</h1>
          <span className={styles.subtitle}>Dashboard</span>
        </div>
        <Controls />
      </header>

      {/* Main content area */}
      <main className={styles.main}>
        {/* Top row: Game Screen + Agent Thoughts */}
        <div className={styles.topRow}>
          <div className={styles.gameScreenWrapper}>
            <GameScreen />
          </div>
          <div className={styles.thoughtsWrapper}>
            <AgentThoughts />
          </div>
        </div>

        {/* Party status bar */}
        <div className={styles.partyRow}>
          <PartyStatus />
        </div>

        {/* Bottom row: Objectives + Event Log */}
        <div className={styles.bottomRow}>
          <div className={styles.objectivesWrapper}>
            <Objectives />
          </div>
          <div className={styles.eventLogWrapper}>
            <EventLog />
          </div>
        </div>
      </main>

      {/* Footer with stats */}
      <footer className={styles.footer}>
        <StatsBar />
      </footer>
    </div>
  );
}

export default App;
