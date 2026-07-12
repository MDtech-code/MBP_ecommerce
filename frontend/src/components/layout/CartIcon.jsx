
import { useCartQuery } from "../../hooks/cart/useCartQueries";
import { Link } from "react-router-dom";
// Replace the static cart block with this:
import { ShoppingCart} from "lucide-react";
export default function CartIcon() {
  const { data: cart } = useCartQuery();
  const totalItems = cart?.total_items ?? 0;

  return (
    <Link
      to="/cart"
      className="flex items-center gap-1.5 font-semibold
                 cursor-pointer hover:text-primary
                 transition-colors relative"
    >
      <ShoppingCart className="w-5 h-5" />
      <span className="hidden lg:inline text-sm">Cart</span>

      {/* Badge — hidden when cart empty */}
      {totalItems > 0 && (
        <span className="absolute -top-2 -right-2 bg-primary
                         text-white text-xs rounded-full w-4 h-4
                         flex items-center justify-center font-bold">
          {totalItems > 99 ? "99+" : totalItems}
        </span>
      )}
    </Link>
  );
}
