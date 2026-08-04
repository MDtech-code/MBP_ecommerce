import {
  ShieldCheck,
  WalletCards,
  Truck,
  RotateCcw,
} from "lucide-react";

export default function HeroBenefits({
  items,
  direction = "horizontal",
  showDivider = true,
}) {

  // ✅ Default fallback (clean & safe)
  const benefitsData = items ?? [
    { id: 1, title: "100% Original Products", icon: ShieldCheck },
    { id: 2, title: "Cash on Delivery", icon: WalletCards },
    { id: 3, title: "Nationwide Delivery", icon: Truck },
    { id: 4, title: "7 Days Easy Returns", icon: RotateCcw },
  ];

  const isHorizontal = direction === "horizontal";

  // ✅ Vertical → only first 3
  const displayItems = isHorizontal
    ? benefitsData
    : benefitsData.slice(0, 3);

  return (
    <div
      className={
        isHorizontal
          ? `flex flex-wrap mt-10 ml-1 ${showDivider ? "divide-x divide-gray-600" : ""}`
          : "flex flex-col space-y-6 mt-10"
      }
    >
      {displayItems.map(({ id, title, icon: Icon }) => (
        <div
          key={id}
          className="relative flex items-center gap-1 px-2 text-white"
        >
          <Icon size={28} className="text-white shrink-0" />

           <span className="absolute left-5 bottom-4 text-primary mx-2">
            •
          </span>

          <span
            className={`text-sm font-semibold leading-tight ${
              isHorizontal ? "wrap-break-word whitespace-normal max-w-25" : ""
            }`}
          >
            {title}
          </span>
        </div>
      ))}
    </div>
  );
}
