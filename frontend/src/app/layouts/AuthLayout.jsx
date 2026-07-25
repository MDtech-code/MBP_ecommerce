import { Link, useLocation, Outlet } from "react-router-dom"
import { useState, useEffect } from "react"
import { Moon, Sun } from "lucide-react"

import { HeroBenefits } from "@shared/ui/HeroBenefits"
import { Logo } from "@shared/ui/Logo"
import { AuthBrand } from "@widgets/auth"
import auth_banner from "@shared/assets/images/accounts/auth_banner.png"

import { AUTH_BRAND_CONFIG } from "./authBrandConfig"

export default function AuthLayout() {
  const { pathname } = useLocation()
  const brandProps = AUTH_BRAND_CONFIG[pathname] || {}

  // Theme Toggle Logic
  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
  if (document.documentElement.classList.contains("dark")) {
    setTimeout(() => setIsDark(true), 0);
  }
}, []);


  const toggleTheme = () => {
    document.documentElement.classList.toggle("dark")
    setIsDark(!isDark)
  }

  return (
    // Restored exact original layout: h-screen, overflow-hidden, and padding to prevent scrollbars
    <main className="h-screen w-full relative overflow-hidden bg-surface dark:bg-[#070707] flex p-0 md:p-4 lg:p-6 font-sans select-none">
      
      {/* 1. Background Image (Hidden on Mobile, Visible Tablet/Desktop) */}
      <div className="hidden md:block absolute inset-0 w-full h-full z-0">
        <img
          src={auth_banner}
          alt="Bike Background"
          className="w-full h-full object-cover object-center pointer-events-none"
        />
        {/* Desktop Gradient vs Tablet Solid Overlay */}
        <div className="hidden lg:block absolute inset-0 bg-linear-to-r from-black/92 via-black/65 to-black/25 pointer-events-none" />
        <div className="block lg:hidden absolute inset-0 bg-black/50 backdrop-blur-sm  pointer-events-none" />
      </div>

      {/* 2. Theme Toggle Button */}
      <button
        onClick={toggleTheme}
        className="absolute top-4 right-4 md:top-8 md:right-8 lg:top-10 lg:right-10 z-50 p-2.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors shadow-sm cursor-pointer touch-manipulation"
        aria-label="Toggle Dark Mode"
      >
        {isDark ? <Sun size={22} /> : <Moon size={22} />}
      </button>

      {/* 3. Main Content Wrapper */}
      <div className="relative z-10 w-full h-full flex justify-center lg:justify-between items-center lg:items-stretch lg:gap-8">
        
        {/* LEFT COLUMN (Desktop Only) - Restored exact original logic */}
        <div className="hidden lg:flex flex-1 flex-col justify-between py-6 pl-6 lg:pl-10">
          <div>
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

        {/* RIGHT COLUMN (Form Card) */}
        {/* Restored original desktop widths, rounded-4xl, and h-full properties */}
        <div className="w-full h-full md:h-auto lg:h-full md:max-w-md lg:max-w-none lg:w-120 xl:w-135 
                        bg-white dark:bg-[#0a0a0a] 
                        md:rounded-4xl 
                        md:shadow-2xl 
                        flex flex-col justify-center 
                        px-6 sm:px-12 lg:px-14 py-10 
                        overflow-y-auto shrink-0 z-20 
                        [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] scrollbar-none">
          
          {/* Mobile & Tablet Branding Header (Disappears on Desktop) */}
          <div className="lg:hidden w-full flex flex-col items-center justify-center mb-6 shrink-0 mt-6 md:mt-0">
            <Link to="/" aria-label="Go to homepage" className="mb-4 block">
              <div className="block dark:hidden">
                <Logo variant="light" size="responsive" />
              </div>
              <div className="hidden dark:block">
                <Logo variant="dark" size="responsive" />
              </div>
            </Link>
            <AuthBrand {...brandProps} />
          </div>

          {/* Restored exact max-w-md constraint for the form */}
          <div className="w-full max-w-md mx-auto my-auto shrink-0 pb-8 md:pb-0">
            <Outlet/>
          </div>
        </div>
      </div>
    </main>
  )
}
// import { Link,useLocation,Outlet}          from "react-router-dom"
// import { HeroBenefits } from "@shared/ui/HeroBenefits"
// import { Logo } from "@shared/ui/Logo"
// import {AuthBrand} from "@widgets/auth";
// import auth_banner from "@shared/assets/images/accounts/auth_banner.png"

// import { AUTH_BRAND_CONFIG } from "./authBrandConfig"

// export default function AuthLayout() {
//   const { pathname } = useLocation()
//   const brandProps = AUTH_BRAND_CONFIG[pathname]
//   return (
//     <main className="h-screen w-full relative overflow-hidden bg-[#070707] flex p-4 sm:p-6 font-sans select-none">
      
//       {/* 1. Background Image */}
//       <img
//         src={auth_banner}
//         alt="Bike Background"
//         className="absolute inset-0 w-full h-full object-cover object-center pointer-events-none"
//       />
//       <div className="absolute inset-0 bg-linear-to-r from-black/92 via-black/65 to-black/25 pointer-events-none" />
//       <div className="relative z-10 w-full h-full flex justify-between items-stretch gap-8">
//         {/* LEFT COLUMN */}
//         <div className="hidden lg:flex flex-1 flex-col justify-between py-6 pl-6 lg:pl-10">
//           <div>
//             {/* Logo */}
//           <Link to="/" aria-label="Go to homepage">
//             <Logo variant="dark" size="lg" />
//           </Link>
//           </div>

//           <div className="my-auto max-w-lg pr-4">
//             <AuthBrand {...brandProps} />
//           </div>

//           <div className="mb-2">
//             <HeroBenefits direction="vertical" showDivider={false} />
//           </div>
//         </div>
//         {/* RIGHT COLUMN */}
//           <div className="w-full lg:w-120 xl:w-135 h-full bg-white rounded-4xl shadow-2xl flex flex-col justify-center px-8 sm:px-12 lg:px-14 py-10 overflow-y-auto shrink-0 z-20 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] scrollbar-none">
//           <div className="w-full max-w-md mx-auto my-auto">
//             <Outlet/>
//           </div>
//         </div>
//       </div>
//     </main>
//   );
// }
