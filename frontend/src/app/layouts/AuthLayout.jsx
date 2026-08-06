//! src/app/layouts/AuthLayout.jsx

// react router import 
import { Link, useLocation, Outlet } from "react-router-dom"


// shared component import 
import { HeroBenefits } from "@shared/ui/HeroBenefits"
import { Logo } from "@shared/ui/Logo"
import {auth_banner} from "@shared/assets"
import {useThemeStore} from "@shared/lib"
import {ThemeToggle} from "@shared/ui"
// widgets components import 
import { AuthBrand } from "@widgets/auth"


// auth pages branding text import 
import { AUTH_BRAND_CONFIG } from "./authBrandConfig"


export default function AuthLayout() {
  const { pathname } = useLocation()
  const brandProps = AUTH_BRAND_CONFIG[pathname] || {}
  const {isDark} =useThemeStore();

  

  return (

    <main className="h-full lg:h-screen w-full relative bg-surface dark:bg-dark font-sans select-none flex p-0 md:p-4 lg:p-6 lg:overflow-hidden">

      {/* Background Image */}
      <div className="hidden md:block absolute inset-0 w-full h-full z-0">
        <img
          src={auth_banner}
          alt="Bike Background"
          className="w-full h-full object-cover object-center pointer-events-none"
        />
        {/* Desktop gradient overlay */}
        <div className="hidden lg:block absolute inset-0 bg-linear-to-r from-black/92 via-black/65 to-black/25 pointer-events-none" />
        {/* Tablet solid dark overlay */}
        <div className="block lg:hidden absolute inset-0 bg-black/50 backdrop-blur-sm pointer-events-none" />
      </div>

      {/* ── 2. Logo — top left on ALL screens ───── */}
      <div className="absolute top-5 left-5 md:top-8 md:left-8 lg:top-10 lg:left-10 z-50">
        <Link to="/" aria-label="Go to homepage">
          {/* Mobile only — variant follows dark mode state */}
          <div className="block md:hidden">
            <Logo variant={isDark ? "dark" : "light"} size="md" />
          </div>
          {/* Tablet and Desktop — always dark, always on image bg */}
          <div className="hidden md:block">
            <Logo variant="dark" size="md" />
          </div>
        </Link>
      </div>

      {/* 3. Theme Toggle */}
      <ThemeToggle/>

      {/* 4. Main Content Wrapper */}
      <div className="relative z-10 w-full min-h-screen lg:min-h-0 lg:h-full flex justify-center lg:justify-between items-center lg:items-stretch lg:gap-8">

        {/* LEFT COLUMN — Desktop only */}
        <div className="hidden lg:flex flex-1 flex-col justify-between py-6 pl-6 lg:pl-10">
          <div className="my-auto max-w-lg pr-4">
            <AuthBrand {...brandProps} />
          </div>
          <div className="mb-2">
            <HeroBenefits direction="vertical" showDivider={false} />
          </div>
        </div>

        {/* RIGHT COLUMN — Form Card ──── */}
        <div className="w-full md:h-auto lg:h-full md:max-w-md lg:max-w-none lg:w-120 xl:w-135
                        bg-white dark:bg-[#0a0a0a]
                        md:rounded-4xl md:shadow-2xl
                        flex flex-col justify-center
                        px-6 sm:px-12 lg:px-14 py-10
                        lg:overflow-y-auto no-scrollbar
                        shrink-0 z-20 md:my-16 lg:my-0">

          {/* Mobile and Tablet Branding Header — hidden on desktop */}
          <div className="lg:hidden w-full flex flex-col items-center justify-center mb-6 shrink-0 mt-6 md:mt-0">
            <AuthBrand {...brandProps} />
          </div>

          {/* Form outlet */}
          <div className="w-full max-w-md mx-auto my-auto shrink-0 pb-8 md:pb-0">
            <Outlet />
          </div>
        </div>
      </div>
    </main>
  )
}
