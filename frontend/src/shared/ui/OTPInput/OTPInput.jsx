// src/shared/ui/OTPInput/index.jsx

/**
 * OTPInput — 6 individual digit boxes.
 *
 * Props:
 *   otp        → array of 6 string values from hook
 *   inputRefs  → ref array from hook
 *   onChange   → (index, value) => void
 *   onKeyDown  → (index, e) => void
 *   onPaste    → (e) => void
 *   disabled   → bool
 *   hasError   → bool — red border on all boxes when true
 */
export default function OTPInput({
  otp,
  inputRefs,
  onChange,
  onKeyDown,
  onPaste,
  disabled = false,
  hasError = false,
}) {
  return (
    <div className="flex gap-3 justify-center" onPaste={onPaste}>
      {otp.map((digit, index) => (
        <input
          key={index}
          ref={(el) => (inputRefs.current[index] = el)}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digit}
          disabled={disabled}
          onChange={(e) => onChange(index, e.target.value)}
          onKeyDown={(e) => onKeyDown(index, e)}
          className={`
            w-12 h-14
            text-center text-xl font-bold
            border-2 rounded-xl
            outline-none
            transition-all
            ${hasError
              ? "border-red-400 bg-red-50 text-red-700"
              : digit
                ? "border-primary bg-primary/5 text-primary"
                : "border-gray-200 bg-white text-gray-900"
            }
            focus:border-primary focus:bg-primary/5
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        />
      ))}
    </div>
  );
}