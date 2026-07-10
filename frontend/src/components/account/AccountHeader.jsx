// src/components/layout/AccountHeader.jsx
import { useState, useRef, useEffect } from "react"
import { ShoppingCart, UserRound, LogOut, User, 
         Package, MapPin, Heart, Shield, ChevronDown } from "lucide-react"
import { Link } from "react-router-dom"
import Logo from "../layout/Logo"
import SearchBar from "../common/SearchBar"
import { useAuthStore } from "../../stores/authStore"

import { getMediaUrl } from "../../utils/media"
import {isPending,handleLogout} from "../../hooks/account/useLogoutForm";

const dropdownLinks = [
  { label: "Profile",   icon: User,    to: "/profile"    },
  { label: "Orders",    icon: Package, to: "/orders"      },
  { label: "Wishlist",  icon: Heart,   to: "/wishlist"    },
  { label: "Addresses", icon: MapPin,  to: "/addresses"   },
  { label: "Security",  icon: Shield,  to: "/security"    },
]

export default function AccountHeader() {
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef(null)

  const user = useAuthStore((state) => state.user)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false)
      }
    }
    if (dropdownOpen) document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [dropdownOpen])

  

  return (
    <header className="bg-white border-b border-gray-100 shadow-sm relative">
      <div className="w-full max-w-360 mx-auto px-4 sm:px-6 lg:px-10">
        <div className="h-16 lg:h-20 flex items-center justify-between gap-4">

          {/* Logo — smaller on mobile */}
          <div className="shrink-0">
            <Logo variant="light" size="responsive" className="hidden md:flex" />
          </div>

          {/* Nav Links — Home + Bike Parts only */}
          <div className="flex items-center gap-5 font-semibold shrink-0">
            <Link
              to="/"
              className="text-sm hover:text-primary transition-colors"
            >
              Home
            </Link>
            <button className="flex items-center gap-1 text-sm hover:text-primary transition-colors">
              Bike Parts <ChevronDown size={14} />
            </button>
          </div>

          {/* Search — full bar on xl, icon below xl */}
          <div className="hidden xl:flex flex-1">
            <SearchBar variant="full" />
          </div>

          {/* Right Actions */}
          <div className="flex items-center gap-3 lg:gap-5 shrink-0">

            {/* Search icon below xl */}
            <div className="xl:hidden">
              <SearchBar variant="icon" />
            </div>

            {/* Avatar Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen((prev) => !prev)}
                className="flex items-center gap-2 hover:text-primary transition-colors"
              >
                {/* Avatar */}
                <div className="w-8 h-8 rounded-full bg-gray-100 
                                flex items-center justify-center overflow-hidden shrink-0">
                  {user?.profile?.avatar ? (
                    <img
                      src={getMediaUrl(user.profile.avatar)}
                      alt={user?.short_name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <UserRound size={18} className="text-gray-400" />
                  )}
                </div>
                {/* Name — hidden on small screens */}
                <span className="hidden lg:inline text-sm font-semibold">
                  {user?.short_name || user?.full_name || "Account"}
                </span>
                <ChevronDown size={14} className="hidden lg:inline" />
              </button>

              {/* Dropdown Menu */}
              {dropdownOpen && (
                <div className="absolute top-12 right-0 w-52 bg-white 
                                border rounded-xl shadow-xl z-50 overflow-hidden">

                  {/* User greeting */}
                  <div className="px-4 py-3 border-b bg-gray-50">
                    <p className="text-xs text-gray-400">Signed in as</p>
                    <p className="text-sm font-bold text-gray-700 truncate">
                      {user?.short_name || user?.full_name || "Account"}
                    </p>
                  </div>

                  {/* Links */}
                  <div className="py-1">
                    {dropdownLinks.map(({ label, icon: Icon, to }) => (
                      <Link
                        key={label}
                        to={to}
                        onClick={() => setDropdownOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm
                                   text-gray-600 hover:bg-primary/10 
                                   hover:text-primary transition-colors"
                      >
                        <Icon size={16} />
                        {label}
                      </Link>
                    ))}
                  </div>

                  {/* Logout */}
                  <div className="border-t py-1">
                    <button
                      onClick={handleLogout}
                      disabled={isPending}
                      className="flex items-center gap-3 px-4 py-2.5 text-sm
                                 w-full text-left text-red-500 
                                 hover:bg-red-50 transition-colors
                                 disabled:opacity-60"
                    >
                      <LogOut size={16} />
                      {isPending ? "Logging out..." : "Logout"}
                    </button>
                  </div>

                </div>
              )}
            </div>

            {/* Cart with badge */}
            <div className="flex items-center gap-1.5 font-semibold 
                            cursor-pointer hover:text-primary 
                            transition-colors relative">
              <ShoppingCart className="w-5 h-5" />
              <span className="hidden lg:inline text-sm">Cart</span>
              <span className="absolute -top-2 -right-2 bg-primary text-white 
                               text-xs rounded-full w-4 h-4 flex items-center 
                               justify-center font-bold">
                0
              </span>
            </div>

          </div>
        </div>
      </div>
    </header>
  )
}
// // src/components/account/AccountHeader.jsx
// import { Search, ShoppingCart, LogOut, UserRound } from "lucide-react"
// import { useNavigate } from "react-router-dom"
// import Logo from "../layout/Logo"
// import { useAuthStore } from "../../stores/authStore"
// import { useLogout } from "../../hooks/account/useAuthMutations"
// import { getMediaUrl } from "../../utils/media"

// export default function AccountHeader() {
//   const navigate = useNavigate()
//   const user = useAuthStore((state) => state.user)
//   const { mutate: logout, isPending } = useLogout()

//   const handleLogout = () => {
//     logout(undefined, {
//       onSuccess: () => navigate("/login"),
//       onError: () => navigate("/login"),
//     })
//   }

//   return (
//     <header className="bg-white border-b border-gray-100 h-20 flex items-center shadow-sm">
//       <div className="w-full px-6 lg:px-10 flex items-center justify-between gap-6">

//         {/* Logo */}
//         <Logo />

//         {/* Search Bar */}
//         <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden flex-1 max-w-xl">
//           <input
//             placeholder="Search for parts (e.g. Brake Shoe, CD70 Chain)"
//             className="flex-1 px-4 py-2.5 outline-none text-sm text-gray-400 bg-white"
//           />
//           <button className="bg-primary text-white px-4 py-2.5 flex items-center justify-center">
//             <Search size={18} />
//           </button>
//         </div>

//         {/* Right Actions */}
//         <div className="flex items-center gap-6">

//           {/* User info */}
//           <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
//             <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center overflow-hidden">
//               {user?.profile?.avatar ? (
//                 <img
//                   src={getMediaUrl(user.profile.avatar)}
//                   alt={user?.short_name}
//                   className="w-full h-full object-cover"
//                 />
//               ) : (
//                 <UserRound size={18} className="text-gray-400" />
//               )}
//             </div>
//             <span>{user?.short_name || user?.full_name || "Account"}</span>
//           </div>

//           {/* Cart */}
//           <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 cursor-pointer relative">
//             <ShoppingCart size={20} className="text-gray-600" />
//             <span>Cart</span>
//             <span className="absolute -top-2 -right-3 bg-primary text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
//               0
//             </span>
//           </div>

//           {/* Logout */}
//           <button
//             onClick={handleLogout}
//             disabled={isPending}
//             className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-primary transition-colors disabled:opacity-60"
//           >
//             <LogOut size={20} />
//             <span>{isPending ? "..." : "Logout"}</span>
//           </button>

//         </div>
//       </div>
//     </header>
//   )
// }
