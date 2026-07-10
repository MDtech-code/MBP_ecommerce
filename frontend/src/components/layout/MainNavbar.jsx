// src/components/layout/MainNavbar.jsx
import { useState } from "react"
import { ShoppingCart, ChevronDown, Menu, UserRound,
         LogOut, User, Package, MapPin, Heart, Shield } from "lucide-react"
import { Link} from "react-router-dom"
import Container from "../common/Container"
import Logo from "./Logo"
import MobileMenu from "./MobileMenu"
import SearchBar from "../common/SearchBar"
import { getMediaUrl } from "../../utils/media"
import {useLogoutForm} from "../../hooks/account/useLogoutForm";

export default function MainNavbar({ user }) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const { isPending,handleLogout} = useLogoutForm();
  
  

  

  return (
    <>
      <nav className="bg-white border-b relative">
        <Container>
          <div className="h-16 lg:h-20 xl:h-24 flex items-center justify-between gap-4">

            {/* Logo */}
            <Link to="/" className="shrink-0">
              <Logo variant="light" size="responsive" />
            </Link>

            {/* Nav Links */}
            <div className="hidden lg:flex items-center gap-6 font-semibold shrink-0">
              <Link to="/" className="text-primary">Home</Link>
              <button className="flex items-center gap-1 hover:text-primary transition-colors">
                Bike Parts <ChevronDown size={15} />
              </button>
              <button className="flex items-center gap-1 hover:text-primary transition-colors">
                Brands <ChevronDown size={15} />
              </button>
              <Link to="/offers" className="hover:text-primary transition-colors">
                Offers
              </Link>
              <Link to="/contact" className="hover:text-primary transition-colors">
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
                    to="/register"
                    className="flex items-center gap-1.5 font-semibold
                               hover:text-primary transition-colors"
                  >
                    <User className="w-5 h-5" />
                    <span className="hidden lg:inline text-sm">Account</span>
                  </Link>

                  <div className="flex items-center gap-1.5 font-semibold
                                  cursor-pointer hover:text-primary transition-colors">
                    <ShoppingCart className="w-5 h-5" />
                    <span className="hidden lg:inline text-sm">Cart</span>
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
                      className="flex items-center gap-2 hover:text-primary transition-colors"
                    >
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
                      <span className="hidden lg:inline text-sm font-semibold">
                        {user?.short_name || user?.full_name || "Account"}
                      </span>
                      <ChevronDown size={14} className="hidden lg:inline" />
                    </button>

                    {/* Dropdown */}
                    {dropdownOpen && (
                      <div className="absolute top-12 right-0 w-52 bg-white
                                      border rounded-xl shadow-xl z-50 overflow-hidden">

                        {/* Greeting */}
                        <div className="px-4 py-3 border-b bg-gray-50">
                          <p className="text-xs text-gray-400">Signed in as</p>
                          <p className="text-sm font-bold text-gray-700 truncate">
                            {user?.short_name || user?.full_name || "Account"}
                          </p>
                        </div>

                        {/* Links */}
                        <div className="py-1">
                          {[
                            { label: "Profile",   icon: User,    to: "/profile"    },
                            { label: "Orders",    icon: Package, to: "/orders"      },
                            { label: "Wishlist",  icon: Heart,   to: "/wishlist"    },
                            { label: "Addresses", icon: MapPin,  to: "/addresses"   },
                            { label: "Security",  icon: Shield,  to: "/security"    },
                          ].map(({ label, icon: Icon, to }) => (
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
                </>
              )}

              {/* Hamburger */}
              <button
                onClick={() => setMenuOpen(true)}
                className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Menu size={22} />
              </button>

            </div>
          </div>
        </Container>
      </nav>

      <MobileMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)} user={user} />
    </>
  )
}
// // src/components/layout/MainNavbar.jsx
// import { useState, useRef, useEffect } from "react";
// import { Search, User, ShoppingCart, ChevronDown, Menu, X } from "lucide-react";
// import { Link } from "react-router-dom";
// import Container from "../common/Container";
// import Logo from "./Logo";
// import MobileMenu from "./MobileMenu";

// export default function MainNavbar() {
//   const [menuOpen, setMenuOpen] = useState(false);
//   const [searchOpen, setSearchOpen] = useState(false);
//   const searchRef = useRef(null);

//   // Close floating search when clicking outside
//   useEffect(() => {
//     function handleClickOutside(e) {
//       if (searchRef.current && !searchRef.current.contains(e.target)) {
//         setSearchOpen(false);
//       }
//     }
//     if (searchOpen) {
//       document.addEventListener("mousedown", handleClickOutside);
//     }
//     return () => document.removeEventListener("mousedown", handleClickOutside);
//   }, [searchOpen]);

//   return (
//     <>
//       <nav className="bg-white border-b relative">
//         <Container>
//           <div className="h-16 lg:h-20 xl:h-24 flex items-center justify-between gap-4">

//             {/* Logo */}
//             <Logo variant="light" size="md" />

//             {/* Desktop Nav Links — only lg+ */}
//             <div className="hidden lg:flex items-center gap-6 font-semibold shrink-0">
//               <Link to="/" className="text-primary">
//                 Home
//               </Link>
//               <button className="flex items-center gap-1 hover:text-primary transition-colors">
//                 Bike Parts <ChevronDown size={15} />
//               </button>
//               <button className="flex items-center gap-1 hover:text-primary transition-colors">
//                 Brands <ChevronDown size={15} />
//               </button>
//               <Link to="/offers" className="hover:text-primary transition-colors">
//                 Offers
//               </Link>
//               <Link to="/contact" className="hover:text-primary transition-colors">
//                 Contact Us
//               </Link>
//             </div>

//             {/* Full Search Bar — xl+ only */}
//             <div className="hidden xl:flex h-11 flex-1 max-w-sm items-center border rounded-full overflow-hidden">
//               <input
//                 type="text"
//                 placeholder="Search parts or bike model..."
//                 className="flex-1 px-4 text-sm outline-none"
//               />
//               <button className="bg-primary text-white px-4 h-full flex items-center justify-center">
//                 <Search size={17} />
//               </button>
//             </div>

           

//             {/* Right Side Actions */}
//             <div className="flex items-center gap-3 lg:gap-5 shrink-0">

//               {/* floating Search Icon  (bellow 1024) */}
//               <div className="flex xl:hidden relative" ref={searchRef}>
//                 <button
//                   onClick={() => setSearchOpen((prev) => !prev)}
//                   className="p-2 rounded-full hover:bg-gray-100 transition-colors"
//                 >
//                   {searchOpen ? <X size={20} /> : <Search size={20} />}
//                 </button>

//                 {/* Floating Search Box */}
//                 {searchOpen && (
//                   <div className="absolute top-16 right-0 w-72 bg-white border 
//                                   rounded-xl shadow-lg overflow-hidden z-50 
//                                   flex items-center">
//                     <input
//                       autoFocus
//                       type="text"
//                       placeholder="Search parts or bike model..."
//                       className="flex-1 px-4 py-2.5 text-sm outline-none"
//                     />
//                     <button className="bg-primary text-white px-4 py-3.5 flex items-center">
//                       <Search size={16} />
//                     </button>
//                   </div>
//                 )}
//               </div>
              

//               {/* Account */}
//               <Link
//                 to="/register"
//                 className="flex items-center gap-1.5 font-semibold 
//                            hover:text-primary transition-colors"
//               >
//                 <User className="w-5 h-5" />
//                 <span className="hidden lg:inline text-sm">Account</span>
//               </Link>

//               {/* Cart — no badge for guest */}
//               <div
//                 className="flex items-center gap-1.5 font-semibold 
//                             cursor-pointer hover:text-primary transition-colors"
//               >
//                 <ShoppingCart className="w-5 h-5" />
//                 <span className="hidden lg:inline text-sm">Cart</span>
//               </div>

//               {/* Hamburger — mobile/tablet only */}
//               <button
//                 onClick={() => setMenuOpen(true)}
//                 className="lg:hidden p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
//               >
//                 <Menu size={22} />
//               </button>

//             </div>
//           </div>
//         </Container>
//       </nav>

//       {/* Mobile Drawer */}
//       <MobileMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)} />
//     </>
//   );
// }