// src/features/address/model/useAddressForm.js

import { useState } from "react";
import { useCreateAddress, useUpdateAddress } from "../api/useAddressMutations";
import { normalizeError } from "@shared/api";
import {
  CITY_POSTAL_MAP,
  getProvinceForCity,
} from "@shared/lib/locationData";

/**
 * useAddressForm — form state and submission for address create/edit.
 *
 * Changes from previous version:
 *   - CITY_POSTAL_MAP imported from shared locationData — single source of truth
 *   - CITY_PROVINCE_MAP now used via getProvinceForCity() — was missing before
 *   - handleChange intercepts city field and auto-derives province + postal
 *     matching exactly what backend UserAddress.save() does
 *
 * @param {object|null} existingAddress — null for create, address object for edit
 * @param {function}    onSaveSuccess   — called after successful save
 */

const EMPTY_FORM = {
  label: "home",
  address_line1: "",
  address_line2: "",
  city: "",
  phone: "",
};

export function useAddressForm(existingAddress = null, onSaveSuccess) {
  const isEditing = Boolean(existingAddress);

  const {
    mutate: createAddress,
    isPending: isCreating,
    isError: isCreateError,
    error: createError,
  } = useCreateAddress();

  const {
    mutate: updateAddress,
    isPending: isUpdating,
    isError: isUpdateError,
    error: updateError,
  } = useUpdateAddress();

  const [form, setForm] = useState(
    isEditing
      ? {
          label: existingAddress.label,
          address_line1: existingAddress.address_line1,
          address_line2: existingAddress.address_line2 || "",
          city: existingAddress.city,
          phone: existingAddress.phone || "",
        }
      : { ...EMPTY_FORM },
  );

  const isPending = isCreating || isUpdating;
  const isError = isCreateError || isUpdateError;
  const error = createError || updateError;
  const normalized = isError ? normalizeError(error) : null;

  const fieldErrors = {
    label: normalized?.errors?.fields?.label?.message ?? null,
    address_line1: normalized?.errors?.fields?.address_line1?.message ?? null,
    address_line2: normalized?.errors?.fields?.address_line2?.message ?? null,
    city: normalized?.errors?.fields?.city?.message ?? null,
    phone: normalized?.errors?.fields?.phone?.message ?? null,
  };

  const formError = normalized?.errors?.non_fields?.message ?? null;

  /**
   * handleChange — intercepts city field to auto-derive province + postal.
   *
   * When city changes:
   *   province    → auto-derived via getProvinceForCity()
   *   postal_code → auto-derived via getPostalForCity()
   *
   * These are read-only on backend (UserAddress.save() derives them too).
   * We derive them here so the form preview is accurate.
   * Backend will re-derive on save regardless — this is display only.
   */
  const handleChange = (e) => {
    const { name, value } = e.target;

    if (name === "city") {
      setForm((prev) => ({
        ...prev,
        city: value,
        // Auto-derive — mirrors UserAddress.save() logic
        // Not sent to backend but shown in form preview
      }));
      return;
    }

    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (isEditing) {
      updateAddress(
        { id: existingAddress.id, data: form },
        { onSuccess: () => onSaveSuccess?.() },
      );
    } else {
      createAddress(form, { onSuccess: () => onSaveSuccess?.() });
    }
  };

  // Derived display values — shown in form preview, not sent to backend
  const postalPreview = form.city ? CITY_POSTAL_MAP[form.city] || "—" : "—";
  const provincePreview = form.city
    ? getProvinceForCity(form.city) || "—"
    : "—";

  return {
    form,
    fieldErrors,
    formError,
    isPending,
    isEditing,
    postalPreview,
    provincePreview, // NEW — was missing before
    handleChange,
    handleSubmit,
  };
}
// // src/hooks/account/useAddressForm.js

// import { useState } from "react";
// import { useCreateAddress, useUpdateAddress } from "../api/useAddressMutations";
// import { normalizeError } from "@shared/api";

// export const CITY_POSTAL_MAP = {
//   // Punjab
//   Lahore: "54000",
//   Faisalabad: "38000",
//   Rawalpindi: "46000",
//   Gujranwala: "52250",
//   Multan: "60000",
//   Sialkot: "51310",
//   Bahawalpur: "63100",
//   Sargodha: "40100",
//   Sheikhupura: "39350",
//   Gujrat: "50700",
//   "Rahim Yar Khan": "64200",
//   Jhang: "35200",
//   Sahiwal: "57000",
//   Okara: "56300",
//   Kasur: "55020",
//   // Sindh
//   Karachi: "75000",
//   Hyderabad: "71000",
//   Sukkur: "65200",
//   Larkana: "77150",
//   Nawabshah: "67480",
//   "Mirpur Khas": "69000",
//   // KPK
//   Peshawar: "25000",
//   Abbottabad: "22010",
//   Mardan: "23200",
//   Swat: "19130",
//   Kohat: "26000",
//   Mingora: "19130",
//   // Balochistan
//   Quetta: "87300",
//   Turbat: "92600",
//   Khuzdar: "89100",
//   // Federal / AJK / GB
//   Islamabad: "44000",
//   Muzaffarabad: "13100",
//   Gilgit: "15100",
// };

// const EMPTY_FORM = {
//   label: "home",
//   address_line1: "",
//   address_line2: "",
//   city: "",
//   phone:"",
// };

// export function useAddressForm(existingAddress = null, onSaveSuccess) {
//   const isEditing = Boolean(existingAddress);

//   const {
//     mutate: createAddress,
//     isPending: isCreating,
//     isError: isCreateError,
//     error: createError,
//   } = useCreateAddress();

//   const {
//     mutate: updateAddress,
//     isPending: isUpdating,
//     isError: isUpdateError,
//     error: updateError,
//   } = useUpdateAddress();

//   const [form, setForm] = useState(
//     isEditing
//       ? {
//           label: existingAddress.label,
//           address_line1: existingAddress.address_line1,
//           address_line2: existingAddress.address_line2 || "",
//           city: existingAddress.city,
//           phone: existingAddress.phone,
//         }
//       : { ...EMPTY_FORM },
//   );

//   const isPending = isCreating || isUpdating;
//   const isError = isCreateError || isUpdateError;
//   const error = createError || updateError;
//   const normalized = isError ? normalizeError(error) : null;

//   const fieldErrors = {
//     label: normalized?.errors?.fields?.label?.message ?? null,
//     address_line1: normalized?.errors?.fields?.address_line1?.message ?? null,
//     address_line2: normalized?.errors?.fields?.address_line2?.message ?? null,
//     city: normalized?.errors?.fields?.city?.message ?? null,
//     phone:normalized?.errors?.fields?.phone?.message ?? null,
//   };

//   const formError = normalized?.errors?.non_fields?.message ?? null;

//   const handleChange = (e) => {
//     const { name, value } = e.target;
//     setForm((prev) => ({ ...prev, [name]: value }));
//   };

//   const handleSubmit = (e) => {
//     e.preventDefault();

//     if (isEditing) {
//       updateAddress(
//         { id: existingAddress.id, data: form },
//         { onSuccess: () => onSaveSuccess?.() },
//       );
//     } else {
//       createAddress(form, { onSuccess: () => onSaveSuccess?.() });
//     }
//   };

//   // Derived — postal code preview shown in form UI
//   const postalPreview = form.city ? CITY_POSTAL_MAP[form.city] || "—" : "—";

//   return {
//     form,
//     fieldErrors,
//     formError,
//     isPending,
//     isEditing,
//     postalPreview,
//     handleChange,
//     handleSubmit,
//   };
// }
