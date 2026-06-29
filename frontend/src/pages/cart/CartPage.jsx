// pages/cart/CartPage.jsx
import { useState } from "react";
import AccountHeader from "../../components/account/AccountHeader";
import CartList from "../../components/cart/CartList";
import CartSummary from "../../components/cart/CartSummary";
import CartTrust from "../../components/cart/CartTrust";
import YouMayAlsoLike from "../../components/cart/YouMayAlsoLike";
import { cartItems, youMayAlsoLike } from "../../data/cart";

export default function CartPage() {
  const [items, setItems] = useState(cartItems);

  return (
    <>
      <AccountHeader />

      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Breadcrumb */}
          <nav className="text-sm text-gray-500 mb-5 flex items-center gap-2">
            <span className="hover:text-primary cursor-pointer">Home</span>
            <span>›</span>
            <span className="text-gray-800">Your Cart</span>
          </nav>

          {/* Title */}
          <h1 className="text-2xl font-black text-gray-900 mb-6">
            Your Cart{" "}
            <span className="text-gray-400 font-bold">
              ({items.length} Items)
            </span>
          </h1>

          {/* Main Grid */}
          <div className="grid lg:grid-cols-4 gap-6">

            {/* Cart List */}
            <div className="lg:col-span-3">
              <CartList items={items} setItems={setItems} />
            </div>

            {/* Summary */}
            <div>
              <CartSummary items={items} />
            </div>

          </div>

          {/* Trust Badges */}
          <CartTrust />

          {/* You May Also Like */}
          <YouMayAlsoLike products={youMayAlsoLike} />

        </div>
      </div>
    </>
  );
}