import { Check } from "lucide-react";

export default function RequirementItem({
  satisfied,
  children,
}) {
  return (
    <div className="flex items-center gap-3">

      <div
        className={`
          w-5
          h-5
          rounded-full
          flex
          items-center
          justify-center
          ${
            satisfied
              ? "bg-green-500 text-white"
              : "bg-gray-200 text-gray-500"
          }
        `}
      >
        <Check size={12} />
      </div>

      <span
        className={`
          text-sm
          ${
            satisfied
              ? "text-green-600"
              : "text-gray-500"
          }
        `}
      >
        {children}
      </span>

    </div>
  );
}