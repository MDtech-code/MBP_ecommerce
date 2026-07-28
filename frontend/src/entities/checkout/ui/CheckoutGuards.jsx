// src/entities/checkout/ui/CheckoutGuards.jsx
import { Navigate } from "react-router-dom"
import { useCheckoutStore } from "@entities/checkout"

/**
 * CheckoutGuard
 * Ensures items were selected before entering /checkout/address.
 * If selectedItemIds is empty → redirect to /cart.
 */
export function CheckoutGuard({ children }) {
  const selectedItemIds = useCheckoutStore((s) => s.selectedItemIds)
  if (selectedItemIds.length === 0) {
    return <Navigate to="/cart" replace />
  }
  return children
}

/**
 * PaymentStepGuard
 * Ensures address step was completed before entering /checkout/payment.
 * Checks both selectedItemIds and addressForm.city.
 */
export function PaymentStepGuard({ children }) {
  const selectedItemIds = useCheckoutStore((s) => s.selectedItemIds)
  const addressCity     = useCheckoutStore((s) => s.addressForm.city)

  if (selectedItemIds.length === 0) {
    return <Navigate to="/cart" replace />
  }
  if (!addressCity) {
    return <Navigate to="/checkout/address" replace />
  }
  return children
}