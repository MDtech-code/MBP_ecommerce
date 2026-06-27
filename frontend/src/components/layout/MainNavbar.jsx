import {Search,User,ShoppingCart,ChevronDown} from "lucide-react";
import Container from "../common/Container";
import Logo from "./Logo";

export default function MainNavbar(){

return (

<nav className="bg-white border-b">
<Container>
<div className="h-24 flex items-center justify-between">
<Logo />
{/* Menu */}

<div className="hidden lg:flex items-center gap-7 font-semibold">

<a className="text-primary">Home</a>
<a className="flex items-center gap-1">Bike Parts<ChevronDown size={15}/></a>
<a className="flex items-center gap-1">Accessories<ChevronDown size={15}/></a>
<a>Brands</a>
<a >Offers</a>
<a>Contact Us</a>
</div>
{/* Search */}

<div className="hidden xl:flex  h-12 items-center border rounded-full overflow-hidden">
  <input type="text" className="flex-1  px-3 outline-none" />
  <button className="bg-primary text-white px-5 h-full flex items-center justify-center">
    <Search size={17}/>
  </button>
</div>

<div className="flex gap-6 items-center">
      {/* Account */}
      <div className="flex items-center gap-1 font-semibold">
        <User className="w-5 h-5" />
        <span>Account</span>
      </div>

      {/* Cart with badge */}
      <div className="relative flex items-center gap-1 font-semibold">
        <ShoppingCart className="w-5 h-5" />
        <span>Cart</span>
        <span className="absolute -top-3 -right-3  bg-primary text-white text-xs font-bold px-2 py-0.5 rounded-full">
          0
        </span>
      </div>
    </div>
</div>
</Container>
</nav>
)
}