// src/components/profile/ProfileEditField.jsx

export default function ProfileEditField({
  label,
  name,
  type = "text",
  value,
  onChange,
  error,
  children,
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
        {label}
      </label>

      {children ? children : (
        <input
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          className={`
            w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
            outline-none transition-colors
            focus:border-primary focus:ring-1 focus:ring-primary/20
            ${error ? "border-red-400 bg-red-50" : "border-gray-200 bg-white"}
          `}
        />
      )}

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}
    </div>
  )
}