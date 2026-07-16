// src/entities/cart/ui/CartTrust.jsx
import { ShieldCheck, RotateCcw, WalletCards, Truck } from "lucide-react";

const data = [
  {
    icon: ShieldCheck,
    title: "100% Genuine Parts",
    sub: "Original quality parts",
  },
  {
    icon: RotateCcw,
    title: "7 Days Return",
    sub: "No questions asked",
  },
  {
    icon: WalletCards,
    title: "Secure Payment",
    sub: "100% secure checkout",
  },
  {
    icon: Truck,
    title: "Fast Shipping",
    sub: "Nationwide delivery",
  },
];

export default function CartTrust() {
  return (
    <div className="grid grid-cols-4 bg-white rounded-xl border border-gray-200 mt-8 divide-x divide-gray-200">
      {data.map(({ title, sub, icon: Icon }) => (
        <div key={title} className="flex items-center gap-4 px-6 py-5">
          <Icon size={28} className="text-gray-700 shrink-0" strokeWidth={1.5} />
          <div>
            <h4 className="font-bold text-sm text-gray-900">{title}</h4>
            <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
}