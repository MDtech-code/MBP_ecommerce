import { useEffect } from "react";
import { useThemeStore } from "./themeStore";

export function useThemeSync() {
  const isDark = useThemeStore((state) => state.isDark);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", isDark);
  }, [isDark]);
}