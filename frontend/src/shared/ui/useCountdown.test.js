import { act, renderHook } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { useCountdown } from "./useCountdown";

it.each([undefined, null, "", "2020-01-01T00:00:00Z", "not-a-date"])("is inactive for missing/elapsed/invalid target %s", (target) => {
  const { result, unmount } = renderHook(() => useCountdown(target));
  expect(result.current).toEqual({ secondsLeft: 0, isActive: false, formatted: "0:00" });
  unmount();
});

it("counts down using wall-clock time, clamps at zero, and cleans up", () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
  const { result, unmount } = renderHook(() => useCountdown("2026-01-01T00:01:02Z"));
  expect(result.current.formatted).toBe("1:02");
  act(() => vi.advanceTimersByTime(2000));
  expect(result.current.formatted).toBe("1:00");
  act(() => vi.advanceTimersByTime(61000));
  expect(result.current).toEqual({ secondsLeft: 0, isActive: false, formatted: "0:00" });
  unmount();
  expect(vi.getTimerCount()).toBe(0);
});

it("immediately updates for a new target and removes the previous timer", () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
  const { result, rerender, unmount } = renderHook(({ target }) => useCountdown(target), { initialProps: { target: "2026-01-01T00:01:00Z" } });
  rerender({ target: "2026-01-01T00:02:00Z" });
  expect(result.current.secondsLeft).toBe(120);
  expect(vi.getTimerCount()).toBe(1);
  rerender({ target: null });
  expect(result.current.isActive).toBe(false);
  expect(vi.getTimerCount()).toBe(0);
  unmount();
});
