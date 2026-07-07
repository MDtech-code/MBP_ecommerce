// src/components/layout/Logo.jsx
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
    },
    // NEW — responsive size, small on mobile grows on laptop
    responsive: {
      img: "w-8 h-8 md:w-15 md:h-10",
      title: "text-lg md:text-xl",
      tagline: "text-[10px] md:text-xs"
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
    <div className="flex items-center">
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
