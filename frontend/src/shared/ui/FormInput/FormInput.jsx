// shared/ui/FormInput.jsx

import { Eye, EyeOff } from "lucide-react";
import { useState, useId, memo } from "react";

function FormInput({
  icon: Icon,
  type = "text",
  placeholder,
  name,
  value,
  onChange,
  onBlur,
  error,
}) {
  const errorId = useId();
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === "password";

  return (
    <div className="flex flex-col gap-1">
      
      <div className="flex items-center gap-3 border border-gray-200 dark:border-gray-700 rounded-lg px-4 py-3 focus-within:border-primary transition-colors">
        {Icon && <Icon size={20} className="text-gray-400 shrink-0" />}

        
        <input
          type={isPassword && showPassword ? "text" : type}
          placeholder={placeholder}
          aria-label={placeholder || name}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          name={name}
          value={value}
          onChange={onChange}
          onBlur={onBlur}
          className="w-full outline-none bg-transparent dark:bg-transparent
                     text-gray-900 dark:text-white
                     placeholder-gray-400 dark:placeholder-gray-500"
        />

       
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

      
      {error && (
        <p id={errorId} className="text-xs text-red-500 dark:text-red-400 pl-1">{error}</p>
      )}
    </div>
  );
}
export default memo(FormInput);