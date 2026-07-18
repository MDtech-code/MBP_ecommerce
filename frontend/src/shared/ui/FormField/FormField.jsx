// src/shared/ui/FormField/FormField.jsx

/**
 * FormField — generic labeled field wrapper.
 *
 * Used anywhere a form needs:
 *   - A label
 *   - An input (default) OR custom control via children slot
 *   - An optional error message
 *
 * Zero domain knowledge — works for profile forms,
 * address forms, auth forms, checkout forms, anything.
 *
 * Props:
 *   label    → field label text
 *   name     → input name attribute
 *   type     → input type (default: "text")
 *   value    → controlled input value
 *   onChange → change handler
 *   error    → error string from validation
 *   children → optional custom control (select, readonly div, etc.)
 *              when passed, replaces the default input entirely
 *
 * Usage (default input):
 *   <FormField
 *     label="Street Address"
 *     name="address_line1"
 *     value={form.address_line1}
 *     onChange={handleChange}
 *     error={fieldErrors.address_line1}
 *   />
 *
 * Usage (custom control via children):
 *   <FormField label="City" name="city" error={fieldErrors.city}>
 *     <select name="city" value={form.city} onChange={handleChange}>
 *       ...
 *     </select>
 *   </FormField>
 */
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
      <label className="text-xs font-semibold text-gray-500
                        uppercase tracking-wide">
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
            ${error
              ? "border-red-400 bg-red-50"
              : "border-gray-200 bg-white"
            }
          `}
        />
      )}

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}
    </div>
  );
}