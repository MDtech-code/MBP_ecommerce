import { ArrowRight } from "lucide-react";
import Container from "../common/Container";
import HeroBenefits from "./HeroBenefits";
import bikeHero from "../../assets/images/hero/bike-hero-1.png";
export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-dark">
      {/* Background glow */}
      <div className="absolute right-0 top-0 w-[40vw] h-full bg-primary/10 blur-3xl pointer-events-none" />

      <Container>
        <div className="relative flex flex-col-reverse lg:flex-row items-center py-16 lg:py-24">

          {/* LEFT CONTENT */}
          <div className="relative z-20 w-full lg:w-1/2 text-center lg:text-left">

            <h1 className="text-white text-2xl sm:text-3xl lg:text-5xl font-black italic leading-tight">
              PREMIUM BIKE PARTS
              <br />
              <span className="text-primary">FOR EVERY RIDE</span>
            </h1>

            <p className="text-white mt-5 text-sm sm:text-base lg:text-lg font-semibold">
              Original Parts
              <span className="text-primary mx-2">•</span>
              Best Prices
              <span className="text-primary mx-2">•</span>
              Fast Delivery Across Pakistan
            </p>

            <button className="mt-7 bg-primary text-white px-6 py-3 rounded-md font-bold inline-flex items-center gap-2">
              SHOP NOW
              <ArrowRight size={18} />
            </button>

            <HeroBenefits direction="horizontal" showDivider />
          </div>

          {/* RIGHT IMAGE */}
          <div className="w-full lg:w-1/2 flex justify-center lg:justify-end mb-10 lg:mb-0">
            <img
              src={bikeHero}
              alt="Sport Bike"
              className="w-[85%] sm:w-[70%] lg:w-full max-w-lg object-contain"
            />
          </div>

        </div>
      </Container>
    </section>
  );
}
// import { ArrowRight } from "lucide-react";

// import Container from "../common/Container";
// import HeroBenefits from "./HeroBenefits";

// import bikeHero from "../../assets/images/hero/bike-hero-1.png";

// export default function Hero() {
//   return (
//     <section className="relative overflow-hidden bg-dark min-h-130">
//       {/* Background red glow */}
//       <div className="absolute right-0 top-0 w-150 h-full bg-primary/10 blur-3xl" />

//       <Container>
//         <div className="relative min-h-130 flex items-center">
//           {/* Left Content */}
//           <div className="relative z-20 w-full lg:w-1/2">
//             <h1 className="text-white text-3xl lg:text-5xl font-black italic leading-none">
//               PREMIUM BIKE PARTS
//               <br />
//               <span className="text-primary">FOR EVERY RIDE</span>
//             </h1>

//             <p className="text-white mt-5 text-lg font-semibold">
//               Original Parts
//               <span className="text-primary mx-2">•</span>
//               Best Prices
//               <span className="text-primary mx-2">•</span>
//               Fast Delivery Across Pakistan
//             </p>

//             <button className="mt-7 bg-primary text-white px-7 py-3 rounded-md font-bold flex items-center gap-3">
//               SHOP NOW
//               <ArrowRight size={20} />
//             </button>

//             <HeroBenefits direction="horizontal" showDivider={true} />
//           </div>

//           {/* Bike Image */}
//           <div className="absolute -right-10 bottom-0 lg:w-187.5 z-10">
//             <img
//               src={bikeHero}
//               alt="Sport Bike"
//               className="w-full object-contain"
//             />
//           </div>
//         </div>
//       </Container>
//     </section>
//   );
// }

