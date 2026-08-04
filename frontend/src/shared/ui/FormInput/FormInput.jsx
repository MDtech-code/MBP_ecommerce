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
      <div className="flex items-center gap-3 border border-gray-200 rounded-lg px-4 py-3 focus-within:border-primary  dark:border-gray-700">
        {Icon && <Icon size={20} className="text-gray-400 shrink-0" />}

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

        {isPassword && (
          <button type="button" onClick={() => setShowPassword(!showPassword)}>
            {showPassword ? (
              <EyeOff size={20} className="text-gray-400" />
            ) : (
              <Eye size={20} className="text-gray-400" />
            )}
          </button>
        )}
      </div>
      {/* Field error — only renders when error exists */}
      {error && <p className="text-xs text-red-500 pl-1">{error}</p>}
    </div>
  );
}
