// src/app/providers/guards/GuestRoute.jsx


import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore } from "@entities/user"

/**
 * GuestRoute — only accessible by unauthenticated users.
 * Authenticated users are redirected to home.
 */
export default function GuestRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
