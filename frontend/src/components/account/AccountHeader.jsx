import { Search, User, ShoppingCart } from "lucide-react";
import Logo from "../layout/Logo";

export default function AccountHeader() {
  return (
    <header className="bg-white border-b border-gray-100 h-20 flex items-center shadow-sm">
      <div className="w-full px-6 lg:px-10 flex items-center justify-between gap-6">

        {/* Logo */}
        <Logo />

        {/* Search Bar */}
        <div className="flex items-center border border-gray-200 rounded-lg overflow-hidden flex-1 max-w-xl">
          <input
            placeholder="Search for parts (e.g. Brake Shoe, CD70 Chain)"
            className="flex-1 px-4 py-2.5 outline-none text-sm text-gray-400 bg-white"
          />
          <button className="bg-primary text-white px-4 py-2.5 flex items-center justify-center">
            <Search size={18} />
          </button>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-6">

          {/* Account */}
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 cursor-pointer">
            <User size={20} className="text-gray-600" />
            <span>Account</span>
          </div>

          {/* Cart */}
          <div className="flex items-center gap-2 text-sm font-semibold text-gray-700 cursor-pointer relative">
            <ShoppingCart size={20} className="text-gray-600" />
            <span>Cart</span>
            <span className="absolute -top-2 -right-3 bg-primary text-white text-xs rounded-full w-5 h-5 flex items-center justify-center font-bold">
              0
            </span>
          </div>

        </div>
      </div>
    </header>
  );
}