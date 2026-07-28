// src/features/checkout/model/useCheckoutAddress.js

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@entities/user";
import { useCheckoutStore } from "@entities/checkout";
import { useAddressListQuery } from "../api/useAddressQueries";

/**
 * useCheckoutAddress — logic hook for /checkout/address step.
 *
 * Responsibilities:
 *   - Fetches user's saved addresses
 *   - Auto-selects default address on first load
 *   - Populates addressForm in checkoutStore from selected address
 *   - Pre-populates full_name from user profile (not on UserAddress model)
 *   - Validates address form completeness before allowing continue
 *   - Handles switching between saved address mode and new address form
 *   - Exposes all state and handlers CheckoutAddressPage needs
 *
 * full_name source:
 *   UserAddress has no full_name field — confirmed from serializer.
 *   full_name for shipping comes from user.full_name on auth store.
 *   When user selects a saved address, full_name is pre-populated
 *   from auth store. User can override it in the form field.
 *
 * phone source:
 *   Address phone is optional on UserAddress (blank allowed).
 *   If address.phone is empty, we fall back to user.profile.phone.
 *   Backend contact_phone property does the same fallback at order time.
 *   We mirror this here so form is pre-populated correctly.
 *
 * addressMode:
 *   "saved" — user picks from existing address cards
 *   "new"   — user fills the inline new address form
 *   If user has no saved addresses, mode starts as "new" automatically.
 */
export function useCheckoutAddress() {
  const navigate = useNavigate();

  // ── Auth store — user data ───────────────────────────────────────────────
  const user = useAuthStore((s) => s.user);
  const fullName = user?.full_name ?? "";
  const profilePhone = user?.profile?.phone ?? "";

  // ── Checkout store ───────────────────────────────────────────────────────
  const selectedItemIds = useCheckoutStore((s) => s.selectedItemIds);
  const addressMode = useCheckoutStore((s) => s.addressMode);
  const selectedAddressId = useCheckoutStore((s) => s.selectedAddressId);
  const addressForm = useCheckoutStore((s) => s.addressForm);
  const shippingFee = useCheckoutStore((s) => s.shippingFee);
  const selectedItems = useCheckoutStore((s) => s.selectedItems);

  const setAddressMode = useCheckoutStore((s) => s.setAddressMode);
  const setSelectedAddressId = useCheckoutStore((s) => s.setSelectedAddressId);
  const populateAddressForm = useCheckoutStore((s) => s.populateAddressForm);
  const updateAddressField = useCheckoutStore((s) => s.updateAddressField);

  // ── Address list query ───────────────────────────────────────────────────
  const { data: addresses = [], isLoading, isError } = useAddressListQuery();

  // ── Auto-select default address on first load ────────────────────────────
  // Runs when addresses finish loading and no address is selected yet.
  // Finds default address first, falls back to first address in list.
  // If no addresses exist, switches to "new" mode automatically.
  useEffect(() => {
    if (isLoading) return;
    if (addresses.length === 0) {
      // No saved addresses — go straight to new address form
      setAddressMode("new");
      return;
    }

    // Only auto-select if nothing selected yet
    // (user may have already picked one on a previous visit to this step)
    if (!selectedAddressId) {
      const defaultAddr = addresses.find((a) => a.is_default) ?? addresses[0];

      _selectAddress(defaultAddr);
    }
  }, [isLoading, addresses.length]);

  // ── Internal: select a saved address and populate form ───────────────────
  // Separated so both auto-select and manual select use identical logic.
  const _selectAddress = (address) => {
    setSelectedAddressId(address.id);
    setAddressMode("saved");

    // phone: use address phone if set, fall back to profile phone
    // mirrors backend contact_phone property
    const phoneToUse = address.phone || profilePhone;

    populateAddressForm(
      {
        ...address,
        phone: phoneToUse,
      },
      fullName, // pre-populate full_name from user profile
    );
  };

  // ── Handlers exposed to CheckoutAddressPage ──────────────────────────────

  /**
   * User clicked a saved address card.
   * @param {object} address — UserAddressSerializer output
   */
  const handleSelectSavedAddress = (address) => {
    _selectAddress(address);
  };

  /**
   * User clicked "Add New Address" — switch to new form mode.
   * Store action clears form and resets selectedAddressId.
   */
  const handleSwitchToNew = () => {
    setAddressMode("new");
  };

  /**
   * User clicked "Use Saved Address" — switch back to saved mode.
   * Only callable when addresses.length > 0.
   * Re-selects the previously selected address or default.
   */
  const handleSwitchToSaved = () => {
    if (addresses.length === 0) return;
    const toSelect =
      addresses.find((a) => a.id === selectedAddressId) ??
      addresses.find((a) => a.is_default) ??
      addresses[0];
    _selectAddress(toSelect);
  };

  /**
   * Address form field changed.
   * Handles city auto-derivation via checkoutStore.updateAddressField.
   * @param {string} field
   * @param {string} value
   */
  const handleAddressFieldChange = (field, value) => {
    updateAddressField(field, value);
  };

  /**
   * Continue to payment step.
   * Only callable when isAddressComplete is true.
   * Guard in CheckoutAddressPage also disables button — this is belt + suspenders.
   */
  const handleContinueToPayment = () => {
    if (!isAddressComplete) return;
    navigate("/checkout/payment");
  };

  // ── Address form completeness validation ─────────────────────────────────
  // All required fields must be non-empty strings.
  // address_line2 is optional — not required.
  // province and postal_code are auto-derived — present when city is set.
  const isAddressComplete = Boolean(
    addressForm.full_name?.trim() &&
    addressForm.phone?.trim() &&
    addressForm.address_line1?.trim() &&
    addressForm.city?.trim() &&
    addressForm.province?.trim() &&
    addressForm.postal_code?.trim(),
  );

  // ── Return ───────────────────────────────────────────────────────────────
  return {
    // Address list
    addresses,
    isLoading,
    isError,

    // Selection state
    addressMode,
    selectedAddressId,

    // Form state
    addressForm,
    shippingFee,
    isAddressComplete,

    // Selected items — for order summary right column
    selectedItems,
    selectedItemIds,

    // Handlers
    handleSelectSavedAddress,
    handleSwitchToNew,
    handleSwitchToSaved,
    handleAddressFieldChange,
    handleContinueToPayment,
  };
}
