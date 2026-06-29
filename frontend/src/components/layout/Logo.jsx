import logo from "../../assets/images/logo/logo.png";
import auth_logo from "../../assets/images/logo/auth_banner_logo.png";

export default function Logo({ variant = "light", size = "md" }) {

  const sizes = {
    sm: {
      img: "w-8 h-8",
      title: "text-lg",
      tagline: "text-[10px]"
    },
    md: {
      img: "w-15 h-10",
      title: "text-xl",
      tagline: "text-xs"
    },
    lg: {
      img: "w-20 h-20",
      title: "text-3xl",
      tagline: "text-sm"
    }
  }

  const variants = {
    light: {
      bike: "text-black",
      express: "text-red-600",
      taglineColor: "text-muted",
      logo: logo
    },
    dark: {
      bike: "text-white",
      express: "text-red-500",
      taglineColor: "text-gray-300",
      logo: auth_logo
    }
  }

  const v = variants[variant]
  const s = sizes[size]

  return (
    <div className="flex items-center ">
      
      <img
        src={v.logo}
        alt="BikeXpress Logo"
        className={`${s.img} object-contain`}
      />

      <div>
        <h1 className={`font-black leading-none ${s.title}`}>
          <span className={v.bike}>BIKE</span>
          <span className={v.express}>XPRESS</span>
        </h1>

        <p className={`${s.tagline} ${v.taglineColor}`}>
          Quality Parts. Smooth Rides.
        </p>
      </div>
    </div>
  )
}



// export default function Logo(){

//   return (
//     <div className="flex items-center gap-2">
//       <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white font-black">B</div>
//       <div>
//         <h1 className="font-black text-xl leading-none">BIKE<span className="text-primary">XPRESS</span></h1>
//         <p className="text-xs text-muted">Quality Parts. Smooth Rides.</p>
//       </div>
//     </div>
//   )
// }