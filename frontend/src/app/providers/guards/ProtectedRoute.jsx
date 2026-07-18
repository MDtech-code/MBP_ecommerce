// src/components/layout/ProtectedRoute.jsx

import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuthStore } from "@entities/user"

export default function ProtectedRoute() {
  const location = useLocation()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isBootstrapping = useAuthStore((state) => state.isBootstrapping)

  // Wait for bootstrap to finish before making any redirect decision
  if (isBootstrapping) return null
  // After bootstrap completes, isAuthenticated is the sole source of truth
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        state={{ from: location }}
        replace
      />
    )
  }

  return <Outlet />
}