import daisyui from "daisyui";
/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}", // scan your React files
    ],
    theme: {
        extend: {
            colors: {
                primary: "#2563eb",   // MBP brand blue
                secondary: "#f59e0b", // MBP brand orange
                neutral: "#1f2937",   // dark gray for text
            },
            fontFamily: {
                sans: ["Inter", "sans-serif"],
            },
        },
    },
    plugins: [daisyui],
    daisyui: {
        themes: [
            {
                mbp: {
                    "primary": "#2563eb",
                    "secondary": "#f59e0b",
                    "accent": "#10b981",
                    "neutral": "#1f2937",
                    "base-100": "#ffffff",
                    "info": "#3b82f6",
                    "success": "#22c55e",
                    "warning": "#facc15",
                    "error": "#ef4444",
                },
            },
            "light",
            "dark",
        ],
    },
};
