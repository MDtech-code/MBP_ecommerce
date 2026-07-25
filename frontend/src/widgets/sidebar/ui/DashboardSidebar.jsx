import { NavLink } from "react-router-dom";
import { User, Shield, Key, ShoppingBag } from "lucide-react";

export default function DashboardSidebar() {
  const navItems = [
    { path: "/profile", label: "My Profile", icon: User },
    { path: "/cart", label: "My Cart", icon: ShoppingBag },
    { path: "/security", label: "Security", icon: Shield },
    { path: "/security/change-password", label: "Change Password", icon: Key },
  ];

  return (
    <aside className="w-full lg:w-64 shrink-0 bg-white dark:bg-[#0a0a0a] border-b lg:border-b-0 lg:border-r border-gray-200/80 dark:border-gray-800/80 
                      relative lg:sticky lg:top-0 lg:h-screen lg:z-20">
      
      {/* ── DESKTOP SIDEBAR HEADER (1024px+) ── */}
      <div className="hidden lg:flex p-6 items-center justify-between border-b border-gray-100 dark:border-gray-800/60">
        <h3 className="text-xs font-black text-gray-400 dark:text-gray-500 uppercase tracking-wider">
          Manage Account
        </h3>
      </div>

      {/* ── NAVIGATION CONTAINER ── */}
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
  );
}
// // src/widgets/sidebar/ui/DashboardSidebar.jsx
// import { NavLink } from "react-router-dom";
// import { User, Shield, Key, ShoppingBag, X } from "lucide-react";

// export default function DashboardSidebar({ onClose }) {
//   const navItems = [
//     { path: "/profile", label: "My Profile", icon: User },
//     { path: "/cart", label: "My Cart", icon: ShoppingBag },
//     { path: "/security", label: "Security", icon: Shield },
//     { path: "/security/change-password", label: "Change Password", icon: Key },
//   ];

//   return (
//     <aside className="w-64 bg-white border-r border-gray-200 h-full flex flex-col shadow-xl lg:shadow-none">
//       <div className="p-6 flex items-center justify-between border-b border-gray-100 lg:border-none">
//         <h3 className="text-xs font-black text-gray-400 uppercase tracking-wider">
//           Manage Account
//         </h3>
//         {/* Close Button for Mobile */}
//         {onClose && (
//           <button
//             onClick={onClose}
//             className="lg:hidden text-gray-400 hover:text-gray-800 transition"
//             aria-label="Close sidebar"
//           >
//             <X size={20} />
//           </button>
//         )}
//       </div>

//       <nav className="flex-1 p-6 space-y-2 overflow-y-auto">
//         {navItems.map(({ path, label, icon: Icon }) => (
//           <NavLink
//             key={path}
//             to={path}
//             end
//             onClick={onClose} // Auto-close drawer on navigation
//             className={({ isActive }) =>
//               `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
//                 isActive
//                   ? "bg-primary text-white shadow-sm"
//                   : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
//               }`
//             }
//           >
//             <Icon size={18} />
//             {label}
//           </NavLink>
//         ))}
//       </nav>
//     </aside>
//   );
// }