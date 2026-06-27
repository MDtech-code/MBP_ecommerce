import {Truck,WalletCards,RotateCcw,PackageSearch,CircleHelp,Phone} from "lucide-react";
import Container from "../common/Container";

export default function TopBar() {

  return (

    <div className="bg-dark text-white text-sm">
      <Container>
        <div className="h-10 flex items-center justify-between">
          {/* Left */}
    <div className="flex items-center gap-6">
        <span className="flex items-center gap-2"><Truck size={16}/>Delivering Across Pakistan</span>
        <span className="flex items-center gap-2"><WalletCards size={16}/>Cash on Delivery Available</span>
        <span className="flex items-center gap-2"><RotateCcw size={16}/>7 Days Easy Returns</span>
    </div>

          {/* Right */}

    <div className="flex items-center gap-6">
        <span className="flex items-center gap-2"><PackageSearch size={16}/>Track Order</span>
        <span className="flex items-center gap-2"><CircleHelp size={16}/>Help Center</span>
        <span className="flex items-center gap-2"><Phone size={16}/>0312 0000000</span>


    </div>
    </div>
      </Container>
    </div>

  )

}