// shared/ui/FormInput.jsx

import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

export default function FormInput({
  icon: Icon,
  type = "text",
  placeholder,
  name,
  value,
  onChange,
  onBlur,
  error,
}) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";

  return (
    <div className="flex flex-col gap-1">
      {/* ── Input row ────────────────────────────────────────────────
          focus-within highlights entire row when any child is focused.
          dark:bg-transparent ensures no browser-injected background
          bleeds through on dark mode.
      ─────────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3 focus-within:border-primary transition-colors">
        {Icon && <Icon size={20} className="text-gray-400 shrink-0" />}

        {/* ── OLD ──────────────────────────────────────────────────
        <input
          type={isPassword && showPassword ? "text" : type}
          placeholder={placeholder}
          name={name}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          className="w-full outline-none text-gray-900 placeholder-gray-400
         dark:text-white dark:placeholder-gray-300"
        />
        ─────────────────────────────────────────────────────────── */}

        {/* ── NEW ──────────────────────────────────────────────────
            bg-transparent + dark:bg-transparent:
              Browser injects its own default background on <input>
              elements. Without this, dark mode shows a white/light
              rectangle inside the dark field before user interacts.
        ─────────────────────────────────────────────────────────── */}
        <input
          type={isPassword && showPassword ? "text" : type}
          placeholder={placeholder}
          name={name}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          className="w-full outline-none bg-transparent dark:bg-transparent
                     text-gray-900 dark:text-white
                     placeholder-gray-400 dark:placeholder-gray-500"
        />

        {/* ── OLD ──────────────────────────────────────────────────
        {isPassword && (
          <button type="button" onClick={() => setShowPassword(!showPassword)}>
            {showPassword ? (
              <EyeOff size={20} className="text-gray-400" />
            ) : (
              <Eye size={20} className="text-gray-400" />
            )}
          </button>
        )}
        ─────────────────────────────────────────────────────────── */}

        {/* ── NEW ──────────────────────────────────────────────────
            cursor-pointer added — clickable button had no cursor
            feedback, felt unresponsive on desktop hover.
            touch-manipulation added — removes 300ms tap delay
            on mobile browsers.
        ─────────────────────────────────────────────────────────── */}
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword((prev) => !prev)}
            className="cursor-pointer touch-manipulation shrink-0 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label={showPassword ? "Hide password" : "Show password"}
          >
            {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
          </button>
        )}
      </div>

      {/* Field error — only renders when error exists */}
      {error && (
        <p className="text-xs text-red-500 dark:text-red-400 pl-1">{error}</p>
      )}
    </div>
  );
}
// import { Eye, EyeOff } from "lucide-react";
// import { useState } from "react";

// export default function FormInput({
//   icon: Icon,
//   type = "text",
//   placeholder,
//   name,
//   value,
//   onChange,
//   onBlur,
//   error,
// }) {
//   const [showPassword, setShowPassword] = useState(false);
//   const isPassword = type === "password";

//   return (
//     <div className="flex flex-col gap-1">
//       <div className="flex items-center gap-3 border border-gray-200 rounded-lg px-4 py-3 focus-within:border-primary  dark:border-gray-700">
//         {Icon && <Icon size={20} className="text-gray-400 shrink-0" />}

//         <input
//           type={isPassword && showPassword ? "text" : type}
//           placeholder={placeholder}
//           name={name}
//           value={value}
//           onChange={onChange}
//           onBlur={onBlur}
//           className="w-full outline-none text-gray-900 placeholder-gray-400
//          dark:text-white dark:placeholder-gray-300"
//         />

//         {isPassword && (
//           <button type="button" onClick={() => setShowPassword(!showPassword)}>
//             {showPassword ? (
//               <EyeOff size={20} className="text-gray-400" />
//             ) : (
//               <Eye size={20} className="text-gray-400" />
//             )}
//           </button>
//         )}
//       </div>
//       {/* Field error — only renders when error exists */}
//       {error && <p className="text-xs text-red-500 pl-1">{error}</p>}
//     </div>
//   );
// }
