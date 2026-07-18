// src/components/layout/TopBar.jsx
import { Truck, WalletCards, RotateCcw, CircleHelp, Phone } from "lucide-react";
import { Container } from "@shared/ui"

export default function TopBar() {
  return (
    <div className="bg-dark text-white text-sm hidden lg:block">
      <Container>
        <div className="h-10 flex items-center justify-between">

          {/* Left — Trust Signals */}
          <div className="flex items-center gap-6">
            <span className="flex items-center gap-2">
              <Truck size={16} />
              Delivering Across Pakistan
            </span>
            <span className="flex items-center gap-2">
              <WalletCards size={16} />
              Cash on Delivery
            </span>
            <span className="flex items-center gap-2">
              <RotateCcw size={16} />
              7 Days Easy Returns
            </span>
          </div>

          {/* Right — Support */}
          <div className="flex items-center gap-6">
            <span className="flex items-center gap-2 cursor-pointer hover:text-gray-300 transition-colors">
              <CircleHelp size={16} />
              Help Center
            </span>
            <span className="flex items-center gap-2">
              <Phone size={16} />
              0312 0000000
            </span>
          </div>

        </div>
      </Container>
    </div>
  );
}
