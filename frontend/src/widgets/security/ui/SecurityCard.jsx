import { ChevronRight } from "lucide-react";

export default function SecurityCard({
  icon: Icon,
  title,
  description,
  status,
  statusColor = "bg-green-100 text-green-700",
  actionText,
  disabled = false,
  onClick,
}) {
  return (
    <div
      className="
        bg-white
        rounded-2xl
        border
        border-gray-200
        p-6
        transition-all
        duration-300
        hover:shadow-lg
      "
    >
      <div className="flex items-start justify-between">

        <div className="flex gap-4">

          <div
            className="
              w-14
              h-14
              rounded-xl
              bg-primary/10
              flex
              items-center
              justify-center
            "
          >
            <Icon
              className="text-primary"
              size={26}
            />
          </div>

          <div>

            <h3 className="text-lg font-bold">
              {title}
            </h3>

            <p className="mt-1 text-sm text-gray-500">
              {description}
            </p>

          </div>

        </div>

        <span
          className={`
            px-3
            py-1
            rounded-full
            text-xs
            font-semibold
            ${statusColor}
          `}
        >
          {status}
        </span>

      </div>

      <div className="mt-6 flex justify-end">

        {disabled ? (

          <button
            disabled
            className="
              px-5
              py-2.5
              rounded-lg
              border
              border-gray-300
              text-gray-400
              cursor-not-allowed
            "
          >
            {actionText}
          </button>

        ) : (

          <button
            onClick={onClick}
            className="
              flex
              items-center
              gap-2
              rounded-lg
              bg-primary
              px-5
              py-2.5
              font-semibold
              text-white
              transition
              hover:opacity-90
            "
          >
            {actionText}

            <ChevronRight size={18} />
          </button>

        )}

      </div>

    </div>
  );
}