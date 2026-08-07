// shared/ui/FormField.jsx
//
// Label-driven input component for dashboard/profile forms.
// Pairs with FormInput (icon-driven, auth layer) — they serve
// different UI patterns and are intentionally separate.
//
// Changes from original:
//   - Full dark mode added across all states
//   - bg-white → bg-white dark:bg-transparent on input
//   - border-gray-200 → adds dark:border-gray-700
//   - text-gray-800 → adds dark:text-white
//   - placeholder → adds dark:placeholder-gray-500
//   - error state bg-red-50 → adds dark:bg-red-900/20
//   - error state border-red-400 → adds dark:border-red-500
//   - error text missing dark:text-red-400 → added
//   - label text-gray-500 → adds dark:text-gray-400
//   - children slot preserved — select, date, custom inputs pass through
//   - focus ring adds dark:ring-primary/20 (was already on some consumers
//     inline but not in the base component)

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

      {/* Label */}
      {label && (
        <label
          htmlFor={name}
          className="text-xs font-semibold uppercase tracking-wide
                     text-gray-500 dark:text-gray-400"
        >
          {label}
        </label>
      )}

      {/* ── OLD ─────────────────────────────────────────────────────
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
      ─────────────────────────────────────────────────────────────── */}

      {/* ── NEW ─────────────────────────────────────────────────────
          Children slot preserved for select, date, custom inputs.
          When no children: renders standard text input.
          Dark mode added across all states:
            - normal: dark:bg-transparent dark:border-gray-700 dark:text-white
            - error:  dark:bg-red-900/20 dark:border-red-500
          bg-white removed from normal state → bg-transparent works
          for both light (inherits white card) and dark (inherits dark card).
          htmlFor + id wired so clicking label focuses input.
      ─────────────────────────────────────────────────────────────── */}
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

      {/* ── OLD ─────────────────────────────────────────────────────
      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}
      ─────────────────────────────────────────────────────────────── */}

      {/* ── NEW — dark variant added ─────────────────────────────── */}
      {error && (
        <p className="text-xs text-red-500 dark:text-red-400 pl-1">
          {error}
        </p>
      )}

    </div>
  );
}
// // src/shared/ui/FormField/FormField.jsx

// /**
//  * FormField — generic labeled field wrapper.
//  *
//  * Used anywhere a form needs:
//  *   - A label
//  *   - An input (default) OR custom control via children slot
//  *   - An optional error message
//  *
//  * Zero domain knowledge — works for profile forms,
//  * address forms, auth forms, checkout forms, anything.
//  *
//  * Props:
//  *   label    → field label text
//  *   name     → input name attribute
//  *   type     → input type (default: "text")
//  *   value    → controlled input value
//  *   onChange → change handler
//  *   error    → error string from validation
//  *   children → optional custom control (select, readonly div, etc.)
//  *              when passed, replaces the default input entirely
//  *
//  * Usage (default input):
//  *   <FormField
//  *     label="Street Address"
//  *     name="address_line1"
//  *     value={form.address_line1}
//  *     onChange={handleChange}
//  *     error={fieldErrors.address_line1}
//  *   />
//  *
//  * Usage (custom control via children):
//  *   <FormField label="City" name="city" error={fieldErrors.city}>
//  *     <select name="city" value={form.city} onChange={handleChange}>
//  *       ...
//  *     </select>
//  *   </FormField>
//  */
// export default function FormField({
//   label,
//   name,
//   type = "text",
//   value,
//   onChange,
//   error,
//   children,
// }) {
//   return (
//     <div className="flex flex-col gap-1">
//       <label className="text-xs font-semibold text-gray-500
//                         uppercase tracking-wide">
//         {label}
//       </label>

//       {children ? children : (
//         <input
//           type={type}
//           name={name}
//           value={value}
//           onChange={onChange}
//           className={`
//             w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
//             outline-none transition-colors
//             focus:border-primary focus:ring-1 focus:ring-primary/20
//             ${error
//               ? "border-red-400 bg-red-50"
//               : "border-gray-200 bg-white"
//             }
//           `}
//         />
//       )}

//       {error && (
//         <p className="text-xs text-red-500">{error}</p>
//       )}
//     </div>
//   );
// }