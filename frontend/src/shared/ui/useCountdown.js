// src/shared/hooks/useCountdown.js
import { useState, useEffect } from "react";

/**
 * Ticks down to a target ISO timestamp, recomputing every second.
 * Centralizes retry-countdown UI so every form that can hit a 429
 * shares one implementation instead of each hook re-deriving
 * Date.now() math independently.
 */
export function useCountdown(targetIso) {
  const [secondsLeft, setSecondsLeft] = useState(() =>
    _secondsUntil(targetIso),
  );

  useEffect(() => {
    if (!targetIso) {
      setSecondsLeft(0);
      return;
    }
    setSecondsLeft(_secondsUntil(targetIso));
    const id = setInterval(
      () => setSecondsLeft(_secondsUntil(targetIso)),
      1000,
    );
    return () => clearInterval(id);
  }, [targetIso]);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;

  return {
    secondsLeft,
    isActive: secondsLeft > 0,
    formatted: `${minutes}:${seconds.toString().padStart(2, "0")}`,
  };
}

const _secondsUntil = (targetIso) =>
  targetIso
    ? Math.max(
        0,
        Math.round((new Date(targetIso).getTime() - Date.now()) / 1000),
      )
    : 0;
