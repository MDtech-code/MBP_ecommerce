// src/widgets/sidebar/ui/DashboardSidebar.jsx
import { NavLink } from "react-router-dom";
import { User, Shield, Key, ShoppingBag, X } from "lucide-react";

export default function DashboardSidebar({ onClose }) {
  const navItems = [
    { path: "/profile", label: "My Profile", icon: User },
    { path: "/cart", label: "My Cart", icon: ShoppingBag },
    { path: "/security", label: "Security", icon: Shield },
    { path: "/security/change-password", label: "Change Password", icon: Key },
  ];

  return (
    <aside className="w-64 bg-white border-r border-gray-200 h-full flex flex-col shadow-xl lg:shadow-none">
      <div className="p-6 flex items-center justify-between border-b border-gray-100 lg:border-none">
        <h3 className="text-xs font-black text-gray-400 uppercase tracking-wider">
          Manage Account
        </h3>
        {/* Close Button for Mobile */}
        {onClose && (
          <button
            onClick={onClose}
            className="lg:hidden text-gray-400 hover:text-gray-800 transition"
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        )}
      </div>

      <nav className="flex-1 p-6 space-y-2 overflow-y-auto">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            end
            onClick={onClose} // Auto-close drawer on navigation
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-colors ${
                isActive
                  ? "bg-primary text-white shadow-sm"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}