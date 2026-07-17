// src/components/layout/ProtectedRoute.jsx

import { Navigate, Outlet } from "react-router-dom"
import { useAuthStore } from "@entities/user"


export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)


  
  
  if (isAuthenticated) {
    return (
      <Navigate
        to="/"
        replace
      />
    )
  }

  return <Outlet />
}