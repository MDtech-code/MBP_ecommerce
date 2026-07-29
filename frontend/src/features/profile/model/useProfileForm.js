// src/features/profile/model/useProfileForm.js

import { useState } from "react";
import { useUpdateProfile } from "../api/useProfileMutations";
import { useAuthStore } from "@entities/user";
import { normalizeError } from "@shared/api";

export function useProfileForm(onSaveSuccess) {
  const user = useAuthStore((state) => state.user);

  const {
    mutate: updateProfile,
    isPending,
    isError,
    error,
  } = useUpdateProfile();

  const [form, setForm] = useState({
    phone: user?.profile?.phone || "",
    date_of_birth: user?.profile?.date_of_birth || "",
    gender: user?.profile?.gender || "",
  });

  // Track only fields the user actually touched
  const [dirty, setDirty] = useState({});

  // Phone is considered verified if backend says so AND user hasn't changed it
  const [phoneVerifiedInSession, setPhoneVerifiedInSession] = useState(false);

  const normalized = isError ? normalizeError(error) : null;

  const fieldErrors = {
    phone: normalized?.errors?.fields?.phone?.message ?? null,
    date_of_birth: normalized?.errors?.fields?.date_of_birth?.message ?? null,
    gender: normalized?.errors?.fields?.gender?.message ?? null,
  };

  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;

  function handleChange(e) {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setDirty((prev) => ({ ...prev, [name]: true }));

    // If user edits the phone field — any prior session verification is void
    if (name === "phone") {
      setPhoneVerifiedInSession(false);
    }
  }

  // Called by usePhoneVerification when OTP confirmed successfully
  function handlePhoneVerified(verifiedPhone) {
    setForm((prev) => ({ ...prev, phone: verifiedPhone }));
    setPhoneVerifiedInSession(true);
    // Mark phone as dirty so the save payload includes it
    setDirty((prev) => ({ ...prev, phone: true }));
  }

  function handleSubmit(e) {
    e.preventDefault();

    // Only send fields the user actually changed
    const payload = Object.fromEntries(
      Object.entries(form).filter(([key]) => dirty[key]),
    );

    if (Object.keys(payload).length === 0) {
      onSaveSuccess?.();
      return;
    }

    updateProfile(payload, {
      onSuccess: () => onSaveSuccess?.(),
    });
  }

  const phoneChangedFromSaved = form.phone !== (user?.profile?.phone || "");
  const isPhoneVerifiedOnAccount = !!user?.profile?.is_phone_verified;

  // Phone shows as verified if:
  // — backend says verified AND user hasn't changed the phone, OR
  // — user just verified it this session
  const isPhoneVerified =
    (isPhoneVerifiedOnAccount && !phoneChangedFromSaved) ||
    phoneVerifiedInSession;

  return {
    form,
    fieldErrors,
    formError,
    formErrorCode,
    isPending,
    isPhoneVerified,
    phoneChangedFromSaved,
    handleChange,
    handleSubmit,
    handlePhoneVerified,
  };
}
// // src/hooks/account/useProfileForm.js
// import { useState } from "react";
// import { useUpdateProfile } from "../api/useProfileMutations";
// import { useAuthStore } from "@entities/user";
// import { normalizeError } from "@shared/api";

// export function useProfileForm(onSaveSuccess) {
//   const user = useAuthStore((state) => state.user);
//   const {
//     mutate: updateProfile,
//     isPending,
//     isError,
//     error,
//   } = useUpdateProfile();

//   const [form, setForm] = useState({
//     phone: user?.profile?.phone || "",
//     date_of_birth: user?.profile?.date_of_birth || "",
//     gender: user?.profile?.gender || "",
//   });

//   const normalized = isError ? normalizeError(error) : null;

//   const fieldErrors = {
//     phone: normalized?.errors?.fields?.phone?.message ?? null,
//     date_of_birth: normalized?.errors?.fields?.date_of_birth?.message ?? null,
//     gender: normalized?.errors?.fields?.gender?.message ?? null,
//   };

//   const formError = normalized?.errors?.non_fields?.message ?? null;

//   const handleChange = (e) => {
//     setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
//   };

//   const handleSubmit = (e) => {
//     e.preventDefault();
//     updateProfile(form, {
//       onSuccess: () => onSaveSuccess?.(),
//     });
//   };

//   return {
//     form,
//     fieldErrors,
//     formError,
//     isPending,
//     handleChange,
//     handleSubmit,
//   };
// }
