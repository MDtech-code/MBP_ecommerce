import { useState, useEffect } from "react";

export function useCountdown(targetIso) {
  const [prevTargetIso, setPrevTargetIso] = useState(targetIso);
  const [secondsLeft, setSecondsLeft] = useState(() => _secondsUntil(targetIso));

  if (targetIso !== prevTargetIso) {
    setPrevTargetIso(targetIso);
    setSecondsLeft(_secondsUntil(targetIso));
  }

  useEffect(() => {
    if (!targetIso) return;

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