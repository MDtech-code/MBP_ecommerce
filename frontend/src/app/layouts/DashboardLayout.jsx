  // import { useState } from "react";
  // import { Header } from "@widgets/header";
  // import { DashboardSidebar } from "@widgets/sidebar";
  // import { Menu } from "lucide-react";

  // export default function DashboardLayout({ children }) {
  //   const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  //   return (
  //     <div className="min-h-screen bg-surface flex flex-col">
  //       {/* Top Header */}
  //       <Header />

  //       {/* Mobile Toolbar */}
  //       <div className="lg:hidden flex items-center justify-between p-4 bg-white border-b border-gray-200">
  //         <span className="font-bold text-gray-900 text-sm">Dashboard Menu</span>
  //         <button
  //           onClick={() => setIsSidebarOpen(true)}
  //           className="p-2 bg-gray-50 border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-100 transition"
  //           aria-label="Open sidebar"
  //         >
  //           <Menu size={20} />
  //         </button>
  //       </div>

  //       <div className="flex flex-1 relative min-h-[calc(100vh-80px)]">
  //         {/* Mobile Drawer Overlay */}
  //         {isSidebarOpen && (
  //           <div
  //             className="fixed inset-0 bg-black/50 z-40 lg:hidden"
  //             onClick={() => setIsSidebarOpen(false)}
  //             aria-hidden="true"
  //           />
  //         )}

  //         {/* Sidebar */}
  //         <div
  //           className={`
  //             fixed inset-y-0 left-0 z-50 w-64 bg-surface lg:bg-transparent transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 lg:w-auto
  //             ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}
  //           `}
  //         >
  //           <DashboardSidebar onClose={() => setIsSidebarOpen(false)} />
  //         </div>

  //         {/* Content */}
  //         <main className="flex-1 p-4 sm:p-6 lg:p-10 w-full overflow-x-hidden">
  //           {children}
  //         </main>
  //       </div>
  //     </div>
  //   );
  // }
// src/app/layouts/DashboardLayout.jsx

import { useState } from "react"
import { Outlet } from "react-router-dom"
import { DashboardSidebar } from "@widgets/sidebar"
import { Menu } from "lucide-react"

export default function DashboardLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <div className="flex flex-1 relative">

      {/* Mobile Toolbar */}
      <div className="lg:hidden flex items-center justify-between p-4 bg-white border-b border-gray-200 fixed top-16 left-0 right-0 z-30">
        <span className="font-bold text-gray-900 text-sm">
          Dashboard Menu
        </span>
        <button
          onClick={() => setIsSidebarOpen(true)}
          className="p-2 bg-gray-50 border border-gray-200 rounded-lg
                     text-gray-600 hover:bg-gray-100 transition"
          aria-label="Open sidebar"
        >
          <Menu size={20} />
        </button>
      </div>

      {/* Mobile Drawer Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <div
        className={`
          fixed inset-y-0 left-0 z-50 w-64 bg-surface
          lg:bg-transparent transform transition-transform
          duration-300 ease-in-out
          lg:relative lg:translate-x-0 lg:w-auto
          ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <DashboardSidebar onClose={() => setIsSidebarOpen(false)} />
      </div>

      {/* Page Content */}
      <main className="flex-1 p-4 sm:p-6 lg:p-10 w-full overflow-x-hidden
                       mt-14 lg:mt-0">
        <Outlet />
      </main>

    </div>
  )
}