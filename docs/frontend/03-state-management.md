# State Management Philosophy

This document defines the rules, boundaries, and best practices for managing data across the BikeExpress frontend. To ensure maximum speed and prevent state synchronization bugs, we use a strict **3-Tier State Separation Strategy**.

---

## The 3-Tier State Taxonomy

Every piece of state in this frontend must live in exactly one of these three buckets:

| State Tier | Technology | Examples | Ownership Location |
| :--- | :--- | :--- | :--- |
| **Server State** | TanStack Query v5 | User profile, Address records, Orders, Products, Cart | The Django Database |
| **Global Client State** | Zustand v5 | Auth flags, current user core details, session bootstrapping | The Browser Memory |
| **Local Component State** | React `useState` | Form fields, active tabs, modal open toggles, accordions | Isolated Component JSX |

---

## 1. Server State (TanStack React Query v5)

### Core Rule:
If the data originates from a Django backend endpoint and is stored in a database, it **must** be managed exclusively by TanStack Query. 

### Configuration (`src/lib/queryClient.js`)
The global `QueryClient` is initialized with strict caching rules to prevent unnecessary over-fetching:
* **`staleTime: 1000 * 60 * 5` (5 Minutes):** Data remains fresh in memory for 5 minutes before a background refetch is even considered.
* **`retry: 1`:** Fails quickly on network drops to maintain UI responsiveness.

### Implementation Pattern (Queries vs Mutations)
Server state interaction is split into automatic caching hooks (Queries) and server-altering actions (Mutations):

```javascript
// src/hooks/account/useAuthMutations.js

// 1. READ query for Profile data
export function useProfile(options = {}) {
  return useQuery({
    queryKey: ["profile"],
    queryFn: accountService.getProfile,
    ...options
  });
}

// 2. WRITE mutation for mutating Address records
export function useCreateAddress() {
  return useMutation({
    mutationFn: accountService.createAddress,
    onSuccess: () => {
      // Invalidate the cache to trigger an automatic background refresh
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
    },
  });
}
```

---

## 2. Global Client State (Zustand v5)

### Core Rule:
Zustand stores are reserved **strictly** for transient data that the client app owns natively, which spans across multiple unrelated pages, and does not originate from a data endpoint.

### Store Architecture (`src/stores/authStore.js`)
Currently, the application contains only one global client store: `authStore`. It handles real-time session tracking and route guarding variables.

```javascript
export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  isBootstrapping: true, // Prevents layout flickering during cold restarts

  setAuth: (user) => set({ isAuthenticated: true, user }),
  clearAuth: () => set({ isAuthenticated: false, user: null }),
  setBootstrapping: (bool) => set({ isBootstrapping: bool }),
}));
```

---

## 3. Local State (React `useState`)

### Core Rule:
If data only matters to a single component or form instance and vanishes when the user navigates away, use primitive React `useState`.

* **Forms:** Form hooks (e.g., `useLoginForm`, `useAddressForm`) leverage local state to capture character keystrokes safely before dispatching to an asynchronous mutation.
* **UI Toggles:** Dropdown expansions, Pakistan city selectors, and avatar modals use local state.

---

## Critical Interaction: How Hooks Connect the Tiers

To see how these systems communicate without polluting each other, inspect this profile save workflow:

```text
[ UI Component (ProfileEditForm) ]
              │
              ▼ Fires onSubmit()
     [ Form Hook (useProfileForm) ]  ──► Manages keystrokes via useState
              │
              ▼ Calls mutate()
   [ Mutation Hook (useUpdateProfile) ] 
              │
              ├──► 1. Calls Django API via accountService
              │
              ▼ On Success Callback
   ┌───────────────────┴───────────────────┐
   ▼                                       ▼
[ Invalidate TanStack Cache ]      [ Update Zustand Store ]
Refetches user data in background   Syncs user profile details instantly
(queryKey: ["profile"])            (useAuthStore.setAuth)
```

---

## Cardinal Anti-Patterns to Prevent

To maintain code health, code reviews must strictly enforce the following taboos:

1. ❌ **Never copy React Query cache data into Zustand.** * *Bad:* Fetching an address array from the backend and immediately dropping it inside a Zustand action.
   * *Consequence:* You create split sources of truth. The UI will render stale information because Zustand misses automatic background invalidations.
2. ❌ **Never save input field keystrokes directly to global stores.**
   * *Consequence:* Triggers aggressive app-wide re-renders on every character type, killing interface rendering speed.
3. ❌ **Never fetch backend APIs inside a Zustand action.**
   * *Consequence:* Violates the **4-Layer Architecture** boundary rules and couples infrastructure directly with client memory stores.