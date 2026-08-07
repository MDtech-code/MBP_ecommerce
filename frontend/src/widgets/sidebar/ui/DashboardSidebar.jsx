// src/widgets/sidebar/DashboardSidebar.jsx


import { NavLink } from "react-router-dom"
import { User, Shield, Key, Package, MessagesSquare, Heart, MapPin } from "lucide-react"

export default function DashboardSidebar() {
  const navItems = [
    { path: "/profile",                  label: "My Profile",       icon: User            },
    { path: "/orders",                   label: "My Orders",        icon: Package         },
    { path: "/reviews",                  label: "My Reviews",       icon: MessagesSquare  },
    { path: "/wishlist",                 label: "My Wishlist",      icon: Heart           },
    { path: "/addresses",                label: "My Addresses",     icon: MapPin          },
    { path: "/security",                 label: "Security",         icon: Shield          },
    { path: "/security/change-password", label: "Change Password",  icon: Key             },
  ]

  return (
    
    <aside className="w-full lg:w-64 shrink-0 bg-white dark:bg-[#0a0a0a]
                      border-b lg:border-b-0 lg:border-r border-gray-200/80
                      dark:border-gray-800/80
                      relative lg:sticky lg:top-16
                      lg:h-[calc(100vh-4rem)] lg:overflow-y-auto no-scrollbar
                      lg:z-20">

      {/* Desktop sidebar header */}
      <div className="hidden lg:flex p-6 items-center justify-between border-b border-gray-100 dark:border-gray-800/60">
        <h3 className="text-xs font-black text-gray-400 dark:text-gray-500 uppercase tracking-wider">
          Manage Account
        </h3>
      </div>

      {/* Navigation */}
      <nav className="flex lg:flex-col gap-1.5 p-3 sm:p-4 lg:p-6 overflow-x-auto no-scrollbar select-none">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold whitespace-nowrap shrink-0 transition-all duration-200 ${
                isActive
                  ? "bg-primary text-white shadow-md shadow-primary/25"
                  : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 hover:text-gray-900 dark:hover:text-white"
              }`
            }
          >
            <Icon size={18} className="shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
// import { NavLink } from "react-router-dom";
// import { User, Shield, Key, Package,MessagesSquare,Heart } from "lucide-react";

// export default function DashboardSidebar() {
//   const navItems = [
//     { path: "/profile", label: "My Profile",  icon: User    },
//     { path: "/orders",  label: "My Orders",   icon: Package },
//     { path: "/reviews", label: "My Reviews", icon:MessagesSquare},
//     { path: "/wishlist", label: "My Wishlist",      icon: Heart          },
//     { path: "/security",label: "Security",    icon: Shield  },
//     { path: "/security/change-password", label: "Change Password", icon: Key },
//   ];

//   return (
//     <aside className="w-full lg:w-64 shrink-0 bg-white dark:bg-[#0a0a0a] border-b lg:border-b-0 lg:border-r border-gray-200/80 dark:border-gray-800/80 
//                       relative lg:sticky lg:top-0 lg:h-screen lg:z-20">

//       {/* ── DESKTOP SIDEBAR HEADER (1024px+) ── */}
//       <div className="hidden lg:flex p-6 items-center justify-between border-b border-gray-100 dark:border-gray-800/60">
//         <h3 className="text-xs font-black text-gray-400 dark:text-gray-500 uppercase tracking-wider">
//           Manage Account
//         </h3>
//       </div>

//       {/* ── NAVIGATION CONTAINER ── */}
//       <nav className="flex lg:flex-col gap-1.5 p-3 sm:p-4 lg:p-6 overflow-x-auto no-scrollbar select-none">
//         {navItems.map(({ path, label, icon: Icon }) => (
//           <NavLink
//             key={path}
//             to={path}
//             end
//             className={({ isActive }) =>
//               `flex items-center gap-2.5 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold whitespace-nowrap shrink-0 transition-all duration-200 ${
//                 isActive
//                   ? "bg-primary text-white shadow-md shadow-primary/25"
//                   : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 hover:text-gray-900 dark:hover:text-white"
//               }`
//             }
//           >
//             <Icon size={18} className="shrink-0" />
//             <span>{label}</span>
//           </NavLink>
//         ))}
//       </nav>
//     </aside>
//   );
// }
