// src/hooks/account/useBootstrapAuth.js
console.log("Bootstrap hook mounted");
import {  useEffect } from "react";
import { accountService } from "../../services/accountService";
import { setAuthToken } from "../../api/auth";
import { useAuthStore } from "../../stores/authStore";

// Module-level — survives StrictMode remounts, resets on true page reload
let bootstrapAttempted = false

export function useBootstrapAuth() {
  console.log('use bootsrat ma hu ab restore method ki targ ja ra hu ')
  // const [isBootstrapping, setIsBootstrapping] = useState(true);
  const setBootstrapping = useAuthStore((state) => state.setBootstrapping);
  const setUser = useAuthStore((state) => state.setUser);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  console.log("isAuthenticated =", isAuthenticated);
  

  useEffect(() => {
    console.log("Effect running");
    // Already authenticated in this session — skip immediately
    if (isAuthenticated) {
      setBootstrapping(false);
      return;
    }

    // User explicitly logged out — do not restore session
    if (sessionStorage.getItem("logged_out") === "true") {
      setBootstrapping(false);
      return;
    }

    // Strict Mode double mount guard
    if (bootstrapAttempted) return;
    bootstrapAttempted = true;

    const restore = async () => {
      console.log("ma restore ma agya hu")
      try {
        console.log('try kar ra hu')
        const refreshResult = await accountService.bootstrap();
        const newAccessToken = refreshResult?.data?.access;

        if (!newAccessToken) {
          // Bootstrap responded but no token — cookie was invalid
          setBootstrapping(false);
          return;
        }

        setAuthToken(newAccessToken);

        // Fetch full profile to populate Zustand store
        const profileResult = await accountService.getProfile();
        setUser(profileResult.data);
      } catch {
        console.log('try to huva ni catch ma agay hu')
        // No cookie, expired cookie, or network error
        // All are silent — user will see login page via ProtectedRoute
      } finally {
        setBootstrapping(false);
      }
    };

    restore();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

}
// // src/hooks/account/useBootstrapAuth.js
// import { useState, useEffect } from "react";
// import { accountService } from "../../services/accountService";
// import { setAuthToken } from "../../api/auth";
// import { useAuthStore } from "../../stores/authStore";

// // Module-level — survives Strict Mode double mount
// let bootstrapPromise = null;

// export function useBootstrapAuth() {
//   const [isBootstrapping, setIsBootstrapping] = useState(true);
//   const setUser = useAuthStore((state) => state.setUser);
//   const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

//   useEffect(() => {
//     // ── Guard 1: Already authenticated in this session ────────────────────
//     if (isAuthenticated) {
//       setIsBootstrapping(false);
//       return;
//     }

//     // ── Guard 2: User explicitly logged out ───────────────────────────────
//     // Do not attempt to restore a session the user intentionally ended
//     if (sessionStorage.getItem("logged_out") === "true") {
//       setIsBootstrapping(false);
//       return;
//     }

//     // ── Bootstrap: restore session from refresh token cookie ──────────────
//     // Module-level promise prevents Strict Mode from calling twice
//     if (!bootstrapPromise) {
//       bootstrapPromise = accountService
//         .bootstrap()
//         .then(async (refreshResult) => {
//           const newAccessToken = refreshResult?.data?.access;
//           if (!newAccessToken) return;

//           setAuthToken(newAccessToken);
//           const profileResult = await accountService.getProfile();
//           setUser(profileResult.data);
//         })
//         .catch(() => {
//           // Cookie missing or expired — silent, expected for logged out users
//         })
//         .finally(() => {
//           bootstrapPromise = null;
//         });
//     }

//     // Both Strict Mode mounts attach to the same promise
//     bootstrapPromise.finally(() => {
//       setIsBootstrapping(false);
//     });
//   }, []);

//   return { isBootstrapping };
// }
// // src/hooks/account/useBootstrapAuth.js

// import { useState, useEffect } from "react";
// import { accountService } from "../../services/accountService";
// import { setAuthToken } from "../../api/auth";
// import { useAuthStore } from "../../stores/authStore";

// let bootstrapPromise = null   // ← module level
// /**
//  * useBootstrapAuth
//  *
//  * Runs ONCE when the app starts.
//  * Attempts to restore the user session using the refresh token cookie.
//  *
//  * Flow:
//  *   1. Call /api/accounts/token/refresh/ with cookie
//  *   2. Success → get new access token → setAuthToken → fetch profile
//  *   3. Fetch profile → setUser in Zustand → isAuthenticated = true
//  *   4. Failure → cookie gone or expired → user must log in manually
//  *
//  * Returns:
//  *   isBootstrapping: true while restoring session
//  *                    app should show loading screen during this time
//  *                    to prevent redirect flicker to /login
//  */
// export function useBootstrapAuth() {
//   const [isBootstrapping, setIsBootstrapping] = useState(true);
//   const setUser = useAuthStore((state) => state.setUser);
//   const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

//   useEffect(() => {
//     setTimeout(() => {
//       // User explicitly logged out — do not attempt restore
//       if (sessionStorage.getItem("logged_out") === "true") {
//         setIsBootstrapping(false);
//         return;
//       }
//     }, 0);

//     // If already authenticated (e.g. navigated within app) skip bootstrap
//     setTimeout(() => {
//       if (isAuthenticated) {
//         setIsBootstrapping(false);
//         return;
//       }
//     }, 0);

//     // If bootstrap already started (Strict Mode second mount)
//     // attach to existing promise instead of starting a new one
//     if (!bootstrapPromise) {
//       bootstrapPromise = accountService
//         .bootstrap()
//         .then(async (refreshResult) => {
//           const newAccessToken = refreshResult?.data?.access;
//           if (!newAccessToken) return;

//           setAuthToken(newAccessToken);
//           const profileResult = await accountService.getProfile();
//           setUser(profileResult.data);
//         })
//         .catch(() => {
//           // No cookie or expired — normal for logged out users
//         })
//         .finally(() => {
//           // Reset so next page load starts fresh
//           bootstrapPromise = null;
//         });
//     }

//     // Both mounts attach to same promise
//     bootstrapPromise.finally(() => {
//       setIsBootstrapping(false);
//     });
//   }, [])

//   return { isBootstrapping }
// }

//     const restore = async () => {
//       try {
//         // Step 1 — get new access token from refresh cookie
//         const refreshResult = await accountService.bootstrap();
//         const newAccessToken = refreshResult.data?.access;

//         if (!newAccessToken) {
//           // No token in response — cookie was invalid or missing
//           setIsBootstrapping(false);
//           return;
//         }

//         // Step 2 — set token in memory so api instance uses it
//         setAuthToken(newAccessToken);

//         // Step 3 — fetch full user profile with new token
//         const profileResult = await accountService.getProfile();
//         setUser(profileResult.data);
//       } catch {
//         // Refresh failed — cookie expired or not present
//         // User will need to log in — this is expected behavior
//         // Do not show any error — just let the app load normally
//       } finally {
//         setIsBootstrapping(false);
//       }
//     };

//     restore();
//   }, []);

//   return { isBootstrapping };
// }
