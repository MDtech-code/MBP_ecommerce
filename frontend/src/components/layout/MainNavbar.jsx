// src/components/layout/MainNavbar.jsx
import { useState, useRef, useEffect } from "react";
import { Search, User, ShoppingCart, ChevronDown, Menu, X } from "lucide-react";
import { Link } from "react-router-dom";
import Container from "../common/Container";
import Logo from "./Logo";
import MobileMenu from "./MobileMenu";

export default function MainNavbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef(null);

  // Close floating search when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (searchRef.current && !searchRef.current.contains(e.target)) {
        setSearchOpen(false);
      }
    }
    if (searchOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [searchOpen]);

  return (
    <>
      <nav className="bg-white border-b relative">
        <Container>
          <div className="h-16 lg:h-20 xl:h-24 flex items-center justify-between gap-4">

            {/* Logo */}
            <Logo variant="light" size="md" />

            {/* Desktop Nav Links — only lg+ */}
            <div className="hidden lg:flex items-center gap-6 font-semibold shrink-0">
              <Link to="/" className="text-primary">
                Home
              </Link>
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

            {/* Full Search Bar — xl+ only */}
            <div className="hidden xl:flex h-11 flex-1 max-w-sm items-center border rounded-full overflow-hidden">
              <input
                type="text"
                placeholder="Search parts or bike model..."
                className="flex-1 px-4 text-sm outline-none"
              />
              <button className="bg-primary text-white px-4 h-full flex items-center justify-center">
                <Search size={17} />
              </button>
            </div>

           

            {/* Right Side Actions */}
            <div className="flex items-center gap-3 lg:gap-5 shrink-0">

              {/* floating Search Icon  (bellow 1024) */}
              <div className="flex xl:hidden relative" ref={searchRef}>
                <button
                  onClick={() => setSearchOpen((prev) => !prev)}
                  className="p-2 rounded-full hover:bg-gray-100 transition-colors"
                >
                  {searchOpen ? <X size={20} /> : <Search size={20} />}
                </button>

                {/* Floating Search Box */}
                {searchOpen && (
                  <div className="absolute top-16 right-0 w-72 bg-white border 
                                  rounded-xl shadow-lg overflow-hidden z-50 
                                  flex items-center">
                    <input
                      autoFocus
                      type="text"
                      placeholder="Search parts or bike model..."
                      className="flex-1 px-4 py-2.5 text-sm outline-none"
                    />
                    <button className="bg-primary text-white px-4 py-3.5 flex items-center">
                      <Search size={16} />
                    </button>
                  </div>
                )}
              </div>
              

              {/* Account */}
              <Link
                to="/register"
                className="flex items-center gap-1.5 font-semibold 
                           hover:text-primary transition-colors"
              >
                <User className="w-5 h-5" />
                <span className="hidden lg:inline text-sm">Account</span>
              </Link>

              {/* Cart — no badge for guest */}
              <div
                className="flex items-center gap-1.5 font-semibold 
                            cursor-pointer hover:text-primary transition-colors"
              >
                <ShoppingCart className="w-5 h-5" />
                <span className="hidden lg:inline text-sm">Cart</span>
              </div>

              {/* Hamburger — mobile/tablet only */}
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

      {/* Mobile Drawer */}
      <MobileMenu isOpen={menuOpen} onClose={() => setMenuOpen(false)} />
    </>
  );
}