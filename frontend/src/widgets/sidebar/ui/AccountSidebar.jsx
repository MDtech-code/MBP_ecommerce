// src/components/account/AccountSidebar.jsx
import { User, Package, MapPin, Heart, Shield, LogOut } from "lucide-react"
import { useNavigate, useLocation } from "react-router-dom"

import { useLogoutForm } from "@features/auth"
const menu = [
  { name: "Profile",   icon: User,    path: "/profile"    },
  { name: "Orders",    icon: Package, path: "/orders"      },
  { name: "Addresses", icon: MapPin,  path: "/addresses"   },
  { name: "Wishlist",  icon: Heart,   path: "/wishlist"    },
  { name: "Security",  icon: Shield,  path: "/security"    },
]

export default function AccountSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isPending,handleLogout} = useLogoutForm();

  

  return (
    <aside className="hidden lg:block w-64 bg-dark text-white">
      <div className="p-6">

        <h2 className="font-bold text-xl mb-8">MY ACCOUNT</h2>

        <div className="space-y-2">

          {menu.map(({ name, icon: Icon, path }) => (
            <div
              key={name}
              onClick={() => navigate(path)}
              className={`
                flex items-center gap-4 px-5 py-4 rounded-lg cursor-pointer
                ${location.pathname === path
                  ? "bg-primary"
                  : "hover:bg-white/10"
                }
              `}
            >
              <Icon size={20} />
              <span className="font-semibold">{name}</span>
            </div>
          ))}

          {/* Logout — separate from nav items */}
          <div
            onClick={handleLogout}
            className={`
              flex items-center gap-4 px-5 py-4 rounded-lg cursor-pointer
              hover:bg-white/10
              ${isPending ? "opacity-60 pointer-events-none" : ""}
            `}
          >
            <LogOut size={20} />
            <span className="font-semibold">
              {isPending ? "Logging out..." : "Logout"}
            </span>
          </div>

        </div>

      </div>
    </aside>
  )
}
