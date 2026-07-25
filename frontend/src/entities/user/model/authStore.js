// src/entities/user/model/authStore.js
import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { createAuthSlice } from "./slices/authSlice";
import { immer } from "zustand/middleware/immer";
import { subscribeWithSelector } from "zustand/middleware";

export const useAuthStore = create(
  devtools(
    subscribeWithSelector(
      immer((...args) => ({
        ...createAuthSlice(...args),
      })),
    ),
    { name: "UserStore" },
  ),
);
