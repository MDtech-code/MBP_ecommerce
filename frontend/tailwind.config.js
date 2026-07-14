import daisyui from "daisyui";
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
        
    
      fontFamily: {
        sans: ["Inter", "Arial", "sans-serif"],
      },
    },
  },
  plugins: [daisyui],
  daisyui: {
    themes: [
      {
        mbp: {
          primary: "#DC2626",

          secondary: "#0B0F14",

          base: "#FFFFFF",

          neutral: "#111827",
        },
      },
    ],
  },
};
