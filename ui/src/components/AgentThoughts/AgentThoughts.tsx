/**
 * AgentThoughts component - displays agent reasoning and decisions.
 */

import { memo, useEffect, useRef } from "react";
import { useGameStore } from "../../stores/gameStore";
import styles from "./AgentThoughts.module.css";

// Agent type colors
const agentColors: Record<string, string> = {
  ORCHESTRATOR: "#a855f7", // Purple
  NAVIGATION: "#3b82f6", // Blue
  BATTLE: "#ef4444", // Red
  MENU: "#22c55e", // Green
};

export const AgentThoughts = memo(function AgentThoughts() {
  const thoughts = useGameStore((state) => state.thoughts);
  const currentAgent = useGameStore((state) => state.engine?.current_agent);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new thoughts arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thoughts]);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>Agent Thoughts</span>
        {currentAgent && (
          <span
            className={styles.currentAgent}
            style={{ backgroundColor: agentColors[currentAgent] || "#666" }}
          >
            {currentAgent}
          </span>
        )}
      </div>
      <div className={styles.thoughtsList} ref={scrollRef}>
        {thoughts.length === 0 ? (
          <div className={styles.empty}>
            No agent thoughts yet. Start the game to see agent reasoning.
          </div>
        ) : (
          thoughts.map((thought, index) => (
            <div key={index} className={styles.thought}>
              <div className={styles.thoughtHeader}>
                <span
                  className={styles.agentBadge}
                  style={{
                    backgroundColor:
                      agentColors[thought.agent_type] || "#666",
                  }}
                >
                  {thought.agent_type}
                </span>
                <span className={styles.action}>{thought.action}</span>
                <span className={styles.timestamp}>
                  {formatTime(thought.timestamp)}
                </span>
              </div>
              <div className={styles.reasoning}>
                {thought.reasoning.length > 200
                  ? thought.reasoning.slice(0, 200) + "..."
                  : thought.reasoning}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
});

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}
