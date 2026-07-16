// src/features/profile/index.js
// Public API of the profile feature.

// api
export { useProfileMutations } from "./api/useProfileMutations";

// model
export { useProfileForm } from "./model/useProfileForm";

// ui
export { default as ProfileEditForm } from "./ui/ProfileEditForm";
export { default as ProfileEditField } from "./ui/ProfileEditField";
export { default as AvatarModal } from "./ui/AvatarModal";
