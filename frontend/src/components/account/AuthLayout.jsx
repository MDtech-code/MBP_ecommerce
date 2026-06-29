import HeroBenefits from "../home/HeroBenefits";
import Logo from "../layout/Logo";
import AuthBrand from "./AuthBrand";
import auth_banner from "../../assets/images/accounts/auth_banner.png";

export default function AuthLayout({ children, brandProps }) {
  return (
    /* Outer frame: 100vh, flexbox, with padding to create the mockup's dark "border" */
    <main className="h-screen w-full relative overflow-hidden bg-[#070707] flex p-4 sm:p-6 font-sans select-none">
      
      {/* 1. Background Image */}
      <img
        src={auth_banner}
        alt="Bike Background"
        className="absolute inset-0 w-full h-full object-cover object-center pointer-events-none"
      />

      {/* 2. GRADIENT OVERLAY (Crucial for mockup look: 90% dark on left for text, 30% on right for bike) */}
      <div className="absolute inset-0 bg-linear-to-r from-black/92 via-black/65 to-black/25 pointer-events-none" />

      {/* 3. Content Wrapper */}
      <div className="relative z-10 w-full h-full flex justify-between items-stretch gap-8">
        
        {/* LEFT COLUMN: Branding (flex-1 claims all remaining space to the left of the card) */}
        <div className="hidden lg:flex flex-1 flex-col justify-between py-6 pl-6 lg:pl-10">
          <div>
            <Logo variant="dark" size="lg" />
          </div>

          <div className="my-auto max-w-lg pr-4">
            <AuthBrand {...brandProps} />
          </div>

          <div className="mb-2">
            <HeroBenefits direction="vertical" showDivider={false} />
          </div>
        </div>

        {/* RIGHT COLUMN: The White Card (Fixed width, h-full stretches it top-to-bottom) */}
        {/* <div className="w-full lg:w-120 xl:w-135 h-full bg-white rounded-4xl shadow-2xl flex flex-col justify-center px-8 sm:px-12 lg:px-14 py-10 overflow-y-auto shrink-0 z-20"> */}
          <div className="w-full lg:w-120 xl:w-135 h-full bg-white rounded-4xl shadow-2xl flex flex-col justify-center px-8 sm:px-12 lg:px-14 py-10 overflow-y-auto shrink-0 z-20 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] scrollbar-none">
          <div className="w-full max-w-md mx-auto my-auto">
            {children}
          </div>
        </div>

      </div>
    </main>
  );
}
// import HeroBenefits from "../home/HeroBenefits";
// import Logo from "../layout/Logo";
// import AuthBrand from "./AuthBrand";
// import auth_banner from "../../assets/images/accounts/auth_banner.png";

// export default function AuthLayout({ children, brandProps }) {
//   return (
//     <main className="h-screen relative overflow-hidden bg-dark">
//       {/* Background */}
//       <img
//         src={auth_banner}
//         alt="Bike"
//         className="absolute inset-0 w-full h-full object-cover"
//       />

//       {/* Overlay */}
//       <div className="absolute inset-0 bg-black/60" />

//       <div className="relative z-10 h-full flex flex-col px-6 lg:px-12 py-6">
//         {/* Top Logo */}
//         <Logo variant="dark" size="lg" />

//         {/* Center area */}
//         <div className="flex-1 grid lg:grid-cols-2 gap-10 mt-6">
//           {/* Left (text + benefits at bottom) */}
//           <div className="hidden lg:flex flex-col justify-between">
//             <AuthBrand {...brandProps} />

//             {/* Benefits should be part of flow (NOT absolute) */}
//             <div className="pb-26">
//               <HeroBenefits direction="vertical" showDivider={false} />
//             </div>
//           </div>

//           {/* Right (card centered vertically) */}
//           <div className="flex items-center justify-end">
//             <div className="bg-white rounded-2xl p-8 shadow-2xl w-full max-w-md">
//               {children}
//             </div>
//           </div>
//         </div>
//       </div>
//     </main>
//   );
// }
//! import HeroBenefits from "../home/HeroBenefits";
// import Logo from "../layout/Logo";
// import AuthBrand from "./AuthBrand";
// import auth_banner from "../../assets/images/accounts/auth_banner.png";

// export default function AuthLayout({ children }) {
//   return (
//     <main className="min-h-screen relative overflow-hidden bg-dark">
//       {/* Background */}
//       <img
//         src={auth_banner}
//         alt="Bike"
//         className="absolute inset-0 w-full h-full object-cover opacity-40"
//       />

//       {/* Overlay */}
//       <div className="absolute inset-0 bg-black/60" />

//       <div className="relative z-10 min-h-screen px-6 lg:px-12 py-8">
//         {/* Top Logo */}
//         <Logo variant="dark" size="lg" />

//         <div className="min-h-[80vh] grid lg:grid-cols-2 items-center gap-10">
//           {/* Left */}
//           <div className="hidden lg:block">
//             <AuthBrand />
//           </div>

//           {/* Right Card */}
//           <div className="bg-white rounded-2xl p-8 shadow-2xl max-w-md w-full ml-auto">
//             {children}
//           </div>
//         </div>

//         {/* Bottom Brand */}
//         <div className="absolute bottom-8 left-12 hidden lg:flex items-center gap-3 text-white">
//           <HeroBenefits/>
//         </div>
//       </div>
//     </main>
//   );
// }



// import AuthBrand from "./AuthBrand";


// export default function AuthLayout({
//   children
// }) {


//   return (

//     <main
//       className="
//         min-h-screen
//         bg-dark
//         flex
//         items-center
//         justify-center
//         px-4
//       "
//     >


//       <div
//         className="
//           w-full
//           max-w-6xl
//           grid
//           lg:grid-cols-2
//           gap-10
//           items-center
//         "
//       >


//         {/* Left Side */}

//         <div className="
//           hidden
//           lg:block
//         ">

//           <AuthBrand />

//         </div>




//         {/* Right Card */}

//         <div
//           className="
//             bg-white
//             rounded-2xl
//             shadow-2xl
//             p-8
//             max-w-md
//             w-full
//             mx-auto
//           "
//         >

//           {children}


//         </div>


//       </div>


//     </main>

//   );

// }