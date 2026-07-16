// src/components/layout/ProtectedRoute.jsx

import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuthStore } from "../../stores/authStore"
import { hasAuthToken } from "../../../shared/lib/authToken"

export default function ProtectedRoute() {
  const location = useLocation()
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const isBootstrapping = useAuthStore((state) => state.isBootstrapping)

  // Wait for bootstrap to finish before making any redirect decision
  if (isBootstrapping) return null
  // After bootstrap completes one of these will be true for valid sessions
  if (!isAuthenticated && !hasAuthToken()) {
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