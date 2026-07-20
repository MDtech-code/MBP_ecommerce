// src/shared/ui/ResendTimer/index.jsx

/**
 * ResendTimer — countdown + resend link.
 *
 * Props:
 *   seconds     → current countdown seconds (0 = resend active)
 *   onResend    → function to call when resend clicked
 *   isResending → bool — show loading state on resend
 */
export default function ResendTimer({ seconds, onResend, isResending }) {
  if (seconds > 0) {
    return (
      <p className="text-sm text-gray-500 text-center">
        Resend code in{" "}
        <span className="font-bold text-gray-700 tabular-nums">
          {String(Math.floor(seconds / 60)).padStart(2, "0")}:
          {String(seconds % 60).padStart(2, "0")}
        </span>
      </p>
    );
  }

  return (
    <button
      type="button"
      onClick={onResend}
      disabled={isResending}
      className="text-sm text-primary font-semibold hover:underline disabled:opacity-50 disabled:cursor-not-allowed mx-auto block"
    >
      {isResending ? "Sending..." : "Resend code"}
    </button>
  );
}