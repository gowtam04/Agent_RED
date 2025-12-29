/**
 * EventLog component - displays scrolling game events.
 */

import { memo, useEffect, useRef } from "react";
import { useGameStore } from "../../stores/gameStore";
import styles from "./EventLog.module.css";

// Event type icons
const eventIcons: Record<string, string> = {
  map_change: "🗺️",
  battle_start: "⚔️",
  battle_end: "✅",
  level_up: "⬆️",
  item_obtained: "📦",
  pokemon_caught: "🔴",
  healed: "💊",
  default: "📝",
};

export const EventLog = memo(function EventLog() {
  const events = useGameStore((state) => state.events);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <span className={styles.title}>Event Log</span>
        <span className={styles.count}>{events.length}</span>
      </div>
      <div className={styles.eventsList} ref={scrollRef}>
        {events.length === 0 ? (
          <div className={styles.empty}>No events yet</div>
        ) : (
          events.map((event, index) => (
            <div key={index} className={styles.event}>
              <span className={styles.timestamp}>
                {formatTime(event.timestamp)}
              </span>
              <span className={styles.icon}>
                {eventIcons[event.event_type] || eventIcons.default}
              </span>
              <span className={styles.description}>{event.description}</span>
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
