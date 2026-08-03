// src/app/App.jsx



import { useEffect } from "react"
import { RouterProvider } from "react-router-dom"
import { router  } from "./providers/router"
import { useBootstrapAuth } from "./providers/useBootstrapAuth"
import { useAuthStore } from "@entities/user"
import {ensureCsrfToken} from "@shared/api"
console.log("app to mount huvi ha ")
function AppContent() {
  useEffect(() => {
    console.log("yar cal to mia bi gya hu")
    ensureCsrfToken();
  }, []);

  useBootstrapAuth()
  const isBootstrapping = useAuthStore((state) => state.isBootstrapping)
  if (isBootstrapping) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-gray-400 text-sm">Loading...</div>
      </div>
    )
  }

  return <RouterProvider router={router} />
}

export default function App() {
  return <AppContent />
}










