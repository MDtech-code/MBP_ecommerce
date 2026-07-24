// src/app/App.jsx

console.log("AppContent render");
import axios from "axios"

axios.interceptors.request.use((config) => {
  if (config.url?.includes("token/refresh")) {
    console.trace("🟡 REFRESH CALLED FROM:", config.url)
  }
  return config
})
import { RouterProvider } from "react-router-dom"
import { router  } from "./providers/router"
import { useBootstrapAuth } from "./providers/useBootstrapAuth"
import { useAuthStore } from "@entities/user"

function AppContent() {

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










