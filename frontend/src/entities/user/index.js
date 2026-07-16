// src/entities/user/index.js
// Public API of the user entity.
// Nothing outside this entity imports from internal paths.

// model
export { useAuthStore } from "./model/authStore";

// ui
export { default as ProfileInfoRow } from "./ui/ProfileInfoRow";
export { default as ProfileView } from "./ui/ProfileView";
export { default as AddressCard } from "./ui/AddressCard";
