import { Moon, Sun } from "lucide-react";
import { useThemeStore } from "@shared/lib/themeStore";

export default function ThemeToggle() {
  const { isDark, toggleTheme } = useThemeStore();

  return (
    <button
      onClick={toggleTheme}
      className="absolute top-4 right-4 md:top-8 md:right-8 lg:top-10 lg:right-10 z-50 p-2.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors shadow-sm cursor-pointer touch-manipulation"
      aria-label="Toggle Dark Mode"
    >
      {isDark ? <Sun size={22} /> : <Moon size={22} />}
    </button>
  );
}