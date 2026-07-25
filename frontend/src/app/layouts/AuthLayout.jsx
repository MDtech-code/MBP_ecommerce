
import { Link,useLocation,Outlet}          from "react-router-dom"
import { HeroBenefits } from "@shared/ui/HeroBenefits"
import { Logo } from "@shared/ui/Logo"
import {AuthBrand} from "@widgets/auth";
import auth_banner from "@shared/assets/images/accounts/auth_banner.png"

import { AUTH_BRAND_CONFIG } from "./authBrandConfig"

export default function AuthLayout() {
  const { pathname } = useLocation()
  const brandProps = AUTH_BRAND_CONFIG[pathname]
  return (
    <main className="h-screen w-full relative overflow-hidden bg-[#070707] flex p-4 sm:p-6 font-sans select-none">
      
      {/* 1. Background Image */}
      <img
        src={auth_banner}
        alt="Bike Background"
        className="absolute inset-0 w-full h-full object-cover object-center pointer-events-none"
      />
      <div className="absolute inset-0 bg-linear-to-r from-black/92 via-black/65 to-black/25 pointer-events-none" />
      <div className="relative z-10 w-full h-full flex justify-between items-stretch gap-8">
        {/* LEFT COLUMN */}
        <div className="hidden lg:flex flex-1 flex-col justify-between py-6 pl-6 lg:pl-10">
          <div>
            {/* Logo */}
          <Link to="/" aria-label="Go to homepage">
            <Logo variant="dark" size="lg" />
          </Link>
          </div>

          <div className="my-auto max-w-lg pr-4">
            <AuthBrand {...brandProps} />
          </div>

          <div className="mb-2">
            <HeroBenefits direction="vertical" showDivider={false} />
          </div>
        </div>
        {/* RIGHT COLUMN */}
          <div className="w-full lg:w-120 xl:w-135 h-full bg-white rounded-4xl shadow-2xl flex flex-col justify-center px-8 sm:px-12 lg:px-14 py-10 overflow-y-auto shrink-0 z-20 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] scrollbar-none">
          <div className="w-full max-w-md mx-auto my-auto">
            <Outlet/>
          </div>
        </div>
      </div>
    </main>
  );
}
