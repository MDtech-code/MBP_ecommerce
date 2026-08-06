// src/shared/lib/themeStore.js

import { create } from "zustand";

export const useThemeStore = create((set) => ({
  isDark: false,

  
  initTheme: () => {
    set({ isDark: document.documentElement.classList.contains("dark") });
  },

  
  toggleTheme: () => set((state) => ({ isDark: !state.isDark })),
}));