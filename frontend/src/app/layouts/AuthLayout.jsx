// src/app/layouts/AuthLayout.jsx

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
   

    
    <main className="h-full lg:h-screen w-full relative bg-surface dark:bg-[#070707] font-sans select-none flex p-0 md:p-4 lg:p-6 lg:overflow-hidden">

      {/* 1. Background Image */}
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

      {/* ── 2. Logo — top left on ALL screens ───────────────────────
          ── OLD ──────────────────────────────────────────────────────
          Three separate div+Logo blocks mounted simultaneously.
          Two of them hidden at any time via display utilities.
          Three Logo instances in the DOM, only one ever visible.

          <div className="absolute top-5 left-5 md:top-8 md:left-8 lg:top-10 lg:left-10 z-50">
            <Link to="/" aria-label="Go to homepage">
              <div className="block md:hidden dark:hidden">
                <Logo variant="light" size="md" />
              </div>
              <div className="hidden dark:block md:dark:hidden">
                <Logo variant="dark" size="md" />
              </div>
              <div className="hidden md:block">
                <Logo variant="dark" size="md" />
              </div>
            </Link>
          </div>
          ──────────────────────────────────────────────────────────────

          ── NEW ───────────────────────────────────────────────────────
          Single Logo instance. Variant decided by one condition:
            - md and above → always dark (sitting on image background)
            - mobile light mode → light (sitting on white card)
            - mobile dark mode → dark (sitting on dark card)
          useLocation already runs at top — no extra hook needed.
          isMdUp derived from a single className-free check is overkill
          here — Tailwind handles it with the wrapper div display trick
          but that brings us back to multiple mounts.
          Cleanest solution: keep two mounts but only two (mobile vs md+)
          instead of three (mobile-light, mobile-dark, md+).
          md:hidden / hidden md:block is the minimal correct split.
      ─────────────────────────────────────────────────────────────── */}
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
      <button
        onClick={toggleTheme}
        className="absolute top-4 right-4 md:top-8 md:right-8 lg:top-10 lg:right-10 z-50 p-2.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors shadow-sm cursor-pointer touch-manipulation"
        aria-label="Toggle Dark Mode"
      >
        {isDark ? <Sun size={22} /> : <Moon size={22} />}
      </button>

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

        {/* RIGHT COLUMN — Form Card
            ── OLD ────────────────────────────────────────────────────
            overflow-y-auto was here but h-full resolved to content
            height on desktop — no constrained height meant the auto
            scroll never triggered. Page scrolled instead of card.
            Three inline scrollbar hacks fighting the global definition
            when .no-scrollbar already exists in index.css.

            className="w-full h-full md:h-auto lg:h-full md:max-w-md
                       lg:max-w-none lg:w-120 xl:w-135
                       bg-white dark:bg-[#0a0a0a]
                       md:rounded-4xl md:shadow-2xl
                       flex flex-col justify-center
                       px-6 sm:px-12 lg:px-14 py-10
                       overflow-y-auto shrink-0 z-20 md:my-16 lg:my-0
                       [&::-webkit-scrollbar]:hidden
                       [-ms-overflow-style:none] scrollbar-none"
            ────────────────────────────────────────────────────────────

            ── NEW ──────────────────────────────────────────────────────
            lg:h-full now works because the parent wrapper has
            lg:h-full and main has lg:h-screen — the full height
            chain is properly established top to bottom.
            lg:overflow-y-auto triggers correctly because the card
            now has a real constrained height to overflow against.
            no-scrollbar replaces the three inline vendor hacks —
            it's the project's own utility defined in index.css
            that handles all three vendor cases cleanly.
            Mobile and tablet: h-auto, natural content flow, untouched.
        ─────────────────────────────────────────────────────────────── */}
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
// import { Link, useLocation, Outlet } from "react-router-dom"
// import { useState, useEffect } from "react"
// import { Moon, Sun } from "lucide-react"

// import { HeroBenefits } from "@shared/ui/HeroBenefits"
// import { Logo } from "@shared/ui/Logo"
// import { AuthBrand } from "@widgets/auth"
// import auth_banner from "@shared/assets/images/accounts/auth_banner.png"

// import { AUTH_BRAND_CONFIG } from "./authBrandConfig"

// export default function AuthLayout() {
//   const { pathname } = useLocation()
//   const brandProps = AUTH_BRAND_CONFIG[pathname] || {}

//   // Theme Toggle Logic
//   const [isDark, setIsDark] = useState(false)

//   useEffect(() => {
//   if (document.documentElement.classList.contains("dark")) {
//     setTimeout(() => setIsDark(true), 0);
//   }
// }, []);


//   const toggleTheme = () => {
//     document.documentElement.classList.toggle("dark")
//     setIsDark(!isDark)
//   }

//   return (
//      <main className="h-full w-full relative bg-surface dark:bg-[#070707] font-sans select-none flex p-0 md:p-4 lg:p-6">
      
//       {/* 1. Background Image  */}
//       <div className="hidden md:block absolute inset-0 w-full h-full z-0">
//         <img
//           src={auth_banner}
//           alt="Bike Background"
//           className="w-full h-full object-cover object-center pointer-events-none"
//         />
//         {/* Desktop Gradient  Overlay */}
//         <div className="hidden lg:block absolute inset-0 bg-linear-to-r from-black/92 via-black/65 to-black/25 pointer-events-none" />
//         {/* Tablet: solid dark overlay */}
//         <div className="block lg:hidden absolute inset-0 bg-black/50 backdrop-blur-sm  pointer-events-none" />
//       </div>


//        {/* ── 2. Logo — top left on ALL screens ───────────────────── */}
//       <div className="absolute top-5 left-5 md:top-8 md:left-8 lg:top-10 lg:left-10 z-50">
//         <Link to="/" aria-label="Go to homepage">
//           {/* Mobile: light logo (on white bg) */}
//           <div className="block md:hidden dark:hidden">
//             <Logo variant="light" size="md" />
//           </div>
//           {/* Mobile dark mode */}
//           <div className="hidden dark:block md:dark:hidden">
//             <Logo variant="dark" size="md" />
//           </div>
//           {/* Tablet + Desktop: always dark logo (on image bg) */}
//           <div className="hidden md:block">
//             <Logo variant="dark" size="md" />
//           </div>
//         </Link>
//       </div>
//       {/* 2. Theme Toggle Button */}
//       <button
//         onClick={toggleTheme}
//         className="absolute top-4 right-4 md:top-8 md:right-8 lg:top-10 lg:right-10 z-50 p-2.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors shadow-sm cursor-pointer touch-manipulation"
//         aria-label="Toggle Dark Mode"
//       >
//         {isDark ? <Sun size={22} /> : <Moon size={22} />}
//       </button>

//       {/* 3. Main Content Wrapper */}
//       <div className="relative z-10 w-full min-h-screen flex justify-center lg:justify-between items-center lg:items-stretch lg:gap-8">
        
//         {/* LEFT COLUMN (Desktop Only) - Restored exact original logic */}
//         <div className="hidden lg:flex flex-1 flex-col justify-between py-6 pl-6 lg:pl-10">
//           {/* <div>
//             <Link to="/" aria-label="Go to homepage">
//               <Logo variant="dark" size="lg" />
//             </Link>
//           </div> */}

//           <div className="my-auto max-w-lg pr-4">
//             <AuthBrand {...brandProps} />
//           </div>

//           <div className="mb-2">
//             <HeroBenefits direction="vertical" showDivider={false} />
//           </div>
//         </div>

//         {/* RIGHT COLUMN (Form Card) */}
//         {/* Restored original desktop widths, rounded-4xl, and h-full properties */}
//         <div className="w-full h-full md:h-auto lg:h-full md:max-w-md lg:max-w-none lg:w-120 xl:w-135 
//                         bg-white dark:bg-[#0a0a0a] 
//                         md:rounded-4xl 
//                         md:shadow-2xl 
//                         flex flex-col justify-center 
//                         px-6 sm:px-12 lg:px-14 py-10 
//                         overflow-y-auto shrink-0 z-20 md:my-16 lg:my-0
//                         [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] scrollbar-none">
          
//           {/* Mobile & Tablet Branding Header (Disappears on Desktop) */}
//           <div className="lg:hidden w-full flex flex-col items-center justify-center mb-6 shrink-0 mt-6 md:mt-0">
//             {/* <Link to="/" aria-label="Go to homepage" className="mb-4 block">
//               <div className="block dark:hidden">
//                 <Logo variant="light" size="responsive" />
//               </div>
//               <div className="hidden dark:block">
//                 <Logo variant="dark" size="responsive" />
//               </div>
//             </Link> */}
//             <AuthBrand {...brandProps} />
//           </div>

//           {/* Restored exact max-w-md constraint for the form */}
//           <div className="w-full max-w-md mx-auto my-auto shrink-0 pb-8 md:pb-0">
//             <Outlet/>
//           </div>
//         </div>
//       </div>
//     </main>
//   )
// }
