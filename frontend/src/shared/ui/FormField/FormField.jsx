// shared/ui/FormField.jsx


export default function FormField({
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

      {label && (
        <label
          htmlFor={name}
          className="text-xs font-semibold uppercase tracking-wide
                     text-gray-500 dark:text-gray-400"
        >
          {label}
        </label>
      )}

      
      {children ? (
        children
      ) : (
        <input
          id={name}
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          className={`
            w-full border rounded-lg px-3 py-2.5 text-sm outline-none
            transition-colors
            text-gray-800 dark:text-white
            placeholder-gray-400 dark:placeholder-gray-500
            focus:border-primary focus:ring-1
            focus:ring-primary/20 dark:focus:ring-primary/20
            ${error
              ? "border-red-400 dark:border-red-500 bg-red-50 dark:bg-red-900/20"
              : "border-gray-200 dark:border-gray-700 bg-transparent dark:bg-transparent"
            }
          `}
        />
      )}

      {error && (
        <p className="text-xs text-red-500 dark:text-red-400 pl-1">
          {error}
        </p>
      )}

    </div>
  );
}
