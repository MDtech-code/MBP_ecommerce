// src/components/layout/MobileMenu.jsx
import { X, Home, Tag, Award, Percent, Phone } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

const menuLinks = [
  { label: "Home", icon: Home, to: "/" },
  { label: "Bike Parts", icon: Tag, to: "/products" },
  { label: "Brands", icon: Award, to: "/brands" },
  { label: "Offers", icon: Percent, to: "/offers" },
  { label: "Contact Us", icon: Phone, to: "/contact" },
];

export default function MobileMenu({ isOpen, onClose }) {
  const location = useLocation();

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 z-40 lg:hidden backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed top-0 left-0  w-72 bg-white z-50 
                      lg:hidden flex flex-col shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 
                        bg-black text-white">
          <span className="font-bold text-base tracking-wide">BikeXpress</span>
          <button
            onClick={onClose}
            className="p-1 rounded-full hover:bg-white/20 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        
        {/* Nav Links */}
        <nav className="flex flex-col px-3 py-3 gap-1 flex-1">
          {menuLinks.map(({ label, icon: Icon, to }) => {
            const isActive = location.pathname === to;
            return (
              <Link
                key={label}
                to={to}
                onClick={onClose}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl
                            font-semibold text-sm transition-all
                            ${isActive
                    ? "bg-primary text-white shadow-sm"
                    : "text-gray-600 hover:bg-primary/10 hover:text-primary"
                  }`}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}
        </nav>


      </div>
    </>
  );
}