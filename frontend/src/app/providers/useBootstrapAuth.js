import { useEffect, useRef } from "react";
import { accountService } from "@shared/api";
import { setAuthToken} from "@shared/lib";
import { useAuthStore } from "@entities/user";

export function useBootstrapAuth() {
  const setBootstrapping = useAuthStore((state) => state.setBootstrapping);
  const setUser = useAuthStore((state) => state.setUser);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // Ref prevents the hook from firing twice on initial load in React 18
  const hasAttempted = useRef(false);

  useEffect(() => {
    // Skip if already auth'd or explicitly logged out
    if (isAuthenticated || sessionStorage.getItem("logged_out") === "true") {
      setBootstrapping(false);
      return;
    }

    if (hasAttempted.current) return;
    hasAttempted.current = true;

    const performBootstrap = async () => {
      try {
        // 1. Proactively hit the refresh endpoint
        const refreshResult = await accountService.bootstrap();

        // IMPORTANT: Ensure this path matches what your backend actually sends!
        // In your interceptor you used response.data.data.access
        // In your previous hook you used refreshResult.data.access
        const newAccessToken = refreshResult.data.access;

        if (!newAccessToken) throw new Error("No token returned");

        // 2. Put token in memory
        setAuthToken(newAccessToken);

        // 3. Fetch profile securely
        const profileResult = await accountService.getProfile();
        setUser(profileResult.data);
      } catch (error) {
        console.warn("Bootstrap phase: No valid session found.", error);
        useAuthStore.getState().logout(); // Ensure Zustand state is fully clean
      } finally {
        setBootstrapping(false);
      }
    };

    performBootstrap();
  }, [isAuthenticated, setBootstrapping, setUser]);
}
// import { useEffect } from "react";
// import { accountService } from "@shared/api";
// import { setAuthToken } from "@shared/lib";
// import { useAuthStore } from "@entities/user";
// import { clearAuth } from "@shared/lib";

// let bootstrapPromise = null;

// export function useBootstrapAuth() {
//   const setBootstrapping = useAuthStore((state) => state.setBootstrapping);
//   const setUser = useAuthStore((state) => state.setUser);
//   const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

//   useEffect(() => {
//     if (isAuthenticated) {
//       setBootstrapping(false);
//       return;
//     }

//     if (sessionStorage.getItem("logged_out") === "true") {
//       setBootstrapping(false);
//       return;
//     }

//     if (bootstrapPromise) {
//       bootstrapPromise.finally(() => setBootstrapping(false));
//       return;
//     }

//     const restore = async () => {
//       try {
//         const refreshResult = await accountService.bootstrap();
//         const newAccessToken = refreshResult?.data?.access;

//         if (!newAccessToken) return;

//         setAuthToken(newAccessToken);
//         try {
//           const profileResult = await accountService.getProfile();
//           setUser(profileResult.data);
//         } catch {
//           clearAuth();
//         }
//       } catch {
//         // Silent failure — user stays unauthenticated
//       }
//     };

//     bootstrapPromise = restore();

//     bootstrapPromise.finally(() => {
//       setBootstrapping(false);
//     });

//     // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, []);
// }
