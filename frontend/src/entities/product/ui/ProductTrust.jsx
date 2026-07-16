// components/product-detail/ProductTrust.jsx
import { ShieldCheck, WalletCards, Truck, RotateCcw } from "lucide-react";

const items = [
  {
    icon: ShieldCheck,
    text: "Original Products",
    sub: "100% Genuine",
  },
  {
    icon: WalletCards,
    text: "Cash On Delivery",
    sub: "Pay when you get",
  },
  {
    icon: Truck,
    text: "Nationwide Delivery",
    sub: "Fast & Reliable",
  },
  {
    icon: RotateCcw,
    text: "7 Days Returns",
    sub: "Hassle free returns",
  },
];

export default function ProductTrust() {
  return (
    <div className="grid grid-cols-4 gap-3 mt-6 border-t border-gray-200 pt-6">
      {items.map(({ text, sub, icon: Icon }) => (
        <div key={text} className="flex items-start gap-2">
          <Icon size={28} className="text-gray-700 shrink-0 mt-0.5" strokeWidth={1.5} />
          <div>
            <p className="text-xs font-bold text-gray-800">{text}</p>
            <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
          </div>
        </div>
      ))}
    </div>
  );
}