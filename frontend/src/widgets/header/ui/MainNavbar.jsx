// src/components/layout/MainNavbar.jsx
import { useState, useRef, useEffect } from "react";
import { ShoppingCart, ChevronDown, Menu, UserRound,
         LogOut, User, Package, MapPin, Heart, Shield } from "lucide-react";
import { Link } from "react-router-dom";
import { Container } from "@shared/ui"
import { Logo } from "@shared/ui"
import MobileMenu from "./MobileMenu";
import { SearchBar } from "@shared/ui"
import { getMediaUrl } from "@shared/lib"
import { useLogoutForm } from "@features/auth"
import BikePartsMegaMenu from "./BikePartsMegaMenu";
import BrandsMegaMenu from "./BrandsMegaMenu";
import { CartIcon } from "@features/cart"
import { useAuthStore }        from "@entities/user"
import { useNavigate }         from "react-router-dom"


/**
 * Which mega menu is open:
 *   null         → none
 *   "bike-parts" → BikePartsMegaMenu
 *   "brands"     → BrandsMegaMenu
 */

export default function MainNavbar({ user }) {
  const [menuOpen, setMenuOpen]       = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [activeMega, setActiveMega]   = useState(null);
const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const navigate        = useNavigate()
  const { isPending, handleLogout } = useLogoutForm();

  // Close mega menu when clicking outside
  const navRef = useRef(null);
  useEffect(() => {
    function handleClickOutside(e) {
      if (navRef.current && !navRef.current.contains(e.target)) {
        setActiveMega(null);
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <>
      <nav className="bg-white  relative z-40" ref={navRef}>
        <Container>
          <div className="h-16 lg:h-20 xl:h-24 flex items-center
                          justify-between gap-4">

            {/* Logo */}
            <Link to="/" className="shrink-0">
              <Logo variant="light" size="responsive" />
            </Link>

            {/* Nav Links */}
            <div className="hidden lg:flex items-center gap-6
                            font-semibold shrink-0">
              <Link to="/" className="text-primary">Home</Link>

              {/* Bike Parts */}
              <button
                onMouseEnter={() => setActiveMega("bike-parts")}
                className={`flex items-center gap-1 transition-colors
                            ${activeMega === "bike-parts"
                              ? "text-primary"
                              : "hover:text-primary"
                            }`}
              >
                Bike Parts
                <ChevronDown
                  size={15}
                  className={`transition-transform duration-200
                              ${activeMega === "bike-parts"
                                ? "rotate-180 text-primary"
                                : ""
                              }`}
                />
              </button>

              {/* Brands */}
              <button
                onMouseEnter={() => setActiveMega("brands")}
                className={`flex items-center gap-1 transition-colors
                            ${activeMega === "brands"
                              ? "text-primary"
                              : "hover:text-primary"
                            }`}
              >
                Brands
                <ChevronDown
                  size={15}
                  className={`transition-transform duration-200
                              ${activeMega === "brands"
                                ? "rotate-180 text-primary"
                                : ""
                              }`}
                />
              </button>

              <Link
                to="/offers"
                className="hover:text-primary transition-colors"
                onMouseEnter={() => setActiveMega(null)}
              >
                Offers
              </Link>
              <Link
                to="/contact"
                className="hover:text-primary transition-colors"
                onMouseEnter={() => setActiveMega(null)}
              >
                Contact Us
              </Link>
            </div>

            {/* Full Search — xl+ */}
            <div className="hidden xl:flex flex-1">
              <SearchBar variant="full" />
            </div>

            {/* Right Side Actions */}
            <div className="flex items-center gap-3 lg:gap-5 shrink-0">

              {/* Search Icon — below xl */}
              <div className="flex xl:hidden">
                <SearchBar variant="icon" />
              </div>

              {/* ── GUEST ── */}
              {!user && (
                <>
                  <Link
                    to="/login"
                    className="flex items-center gap-1.5 font-semibold
                               hover:text-primary transition-colors"
                  >
                    <User className="w-5 h-5" />
                    <span className="hidden lg:inline text-sm">Account</span>
                  </Link>

                  <div className="flex items-center gap-1.5 font-semibold
                                  cursor-pointer hover:text-primary
                                  transition-colors">
                    <ShoppingCart className="w-5 h-5" />
                    
                   <span
  className="hidden lg:inline text-sm cursor-pointer"
  onClick={() => navigate(isAuthenticated ? "/cart" : "/login")}
>
  Cart
</span>

                  </div>
                </>
              )}

              {/* ── AUTH USER ── */}
              {user && (
                <>
                  {/* Avatar Dropdown */}
                  <div className="relative">
                    <button
                      onClick={() => setDropdownOpen((prev) => !prev)}
                      className="flex items-center gap-2
                                 hover:text-primary transition-colors"
                    >
                      <div className="w-8 h-8 rounded-full bg-gray-100
                                      flex items-center justify-center
                                      overflow-hidden shrink-0">
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
                      <span className="hidden lg:inline text-sm font-semibold">
                        {user?.short_name || user?.full_name || "Account"}
                      </span>
                      <ChevronDown size={14} className="hidden lg:inline" />
                    </button>

                    {dropdownOpen && (
                      <div className="absolute top-12 right-0 w-52 bg-white
                                      border rounded-xl shadow-xl z-50
                                      overflow-hidden">
                        <div className="px-4 py-3 border-b bg-gray-50">
                          <p className="text-xs text-gray-400">Signed in as</p>
                          <p className="text-sm font-bold text-gray-700 truncate">
                            {user?.short_name || user?.full_name || "Account"}
                          </p>
                        </div>
                        <div className="py-1">
                          {[
                            { label: "Profile",   icon: User,    to: "/profile"   },
                            { label: "Orders",    icon: Package, to: "/orders"    },
                            { label: "Wishlist",  icon: Heart,   to: "/wishlist"  },
                            { label: "Addresses", icon: MapPin,  to: "/addresses" },
                            { label: "Security",  icon: Shield,  to: "/security"  },
                          ].map(({ label, icon: Icon, to }) => (
                            <Link
                              key={label}
                              to={to}
                              onClick={() => setDropdownOpen(false)}
                              className="flex items-center gap-3 px-4 py-2.5
                                         text-sm text-gray-600 hover:bg-primary/10
                                         hover:text-primary transition-colors"
                            >
                              <Icon size={16} />
                              {label}
                            </Link>
                          ))}
                        </div>
                        <div className="border-t py-1">
                          <button
                            onClick={handleLogout}
                            disabled={isPending}
                            className="flex items-center gap-3 px-4 py-2.5
                                       text-sm w-full text-left text-red-500
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

                  {/* Cart */}
                  {/* <div className="flex items-center gap-1.5 font-semibold
                                  cursor-pointer hover:text-primary
                                  transition-colors relative">
                    <ShoppingCart className="w-5 h-5" />
                    <span className="hidden lg:inline text-sm">Cart</span>
                    <span className="absolute -top-2 -right-2 bg-primary
                                     text-white text-xs rounded-full w-4 h-4
                                     flex items-center justify-center
                                     font-bold">
                      0
                    </span>
                  </div> */}
                  <CartIcon/>
                </>
              )}

              {/* Hamburger */}
              <button
                onClick={() => setMenuOpen(true)}
                className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100
                           transition-colors"
              >
                <Menu size={22} />
              </button>
            </div>
          </div>
        </Container>

        {/* ── Mega Menus ────────────────────────────────────────────────────── */}
        {activeMega === "bike-parts" && (
          <BikePartsMegaMenu onClose={() => setActiveMega(null)} />
        )}
        {activeMega === "brands" && (
          <BrandsMegaMenu onClose={() => setActiveMega(null)} />
        )}
      </nav>

      <MobileMenu
        isOpen={menuOpen}
        onClose={() => setMenuOpen(false)}
        user={user}
      />
    </>
  );
}
