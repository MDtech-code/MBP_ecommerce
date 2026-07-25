// src/app/layouts/RootLayout.jsx

import { Outlet } from "react-router-dom"
import { Header } from "@widgets/header"
import { Footer } from "@widgets/footer"

export default function RootLayout() {
  return (
    <div className="min-h-screen bg-surface">
      <Header />
      <main>
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}