console.log("Bootstrap hook mounted");
import { useEffect, useRef } from "react";
import { accountService } from "@shared/api";
import { setAuthToken } from "@shared/lib";
import { useAuthStore } from "@entities/user";

export function useBootstrapAuth() {
  console.log("use bootsrat ma hu ab restore method ki targ ja ra hu ");
  // const [isBootstrapping, setIsBootstrapping] = useState(true);
  const setBootstrapping = useAuthStore((state) => state.setBootstrapping);
  const setUser = useAuthStore((state) => state.setUser);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const bootstrapAttempted = useRef(false);

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
    if (bootstrapAttempted.current) return;
    bootstrapAttempted.current = true;

    const controller = new AbortController();
    const { signal } = controller;

    const restore = async () => {
      console.log("ma restore ma agya hu");
      try {
        console.log("try kar ra hu");
        const refreshResult = await accountService.bootstrap({ signal });
        if (signal.aborted) return;
        const newAccessToken = refreshResult?.data?.access;

        if (!newAccessToken) {
          // Bootstrap responded but no token — cookie was invalid
          if (!signal.aborted) {
            setBootstrapping(false);
          }
          return;
        }

        setAuthToken(newAccessToken);

        // Fetch full profile to populate Zustand store
        const profileResult = await accountService.getProfile({ signal });
        if (signal.aborted) return;
        setUser(profileResult.data);
      } catch (error) {
        console.log("try to huva ni catch ma agay hu");
        // No cookie, expired cookie, or network error
        // All are silent — user will see login page via ProtectedRoute
        if (
          signal.aborted ||
          error?.name === "CanceledError" ||
          error?.name === "AbortError"
        ) {
          return;
        }
      } finally {
        if (!signal.aborted) {
          setBootstrapping(false);
        }
      }
    };

    restore();

    return () => {
      controller.abort();
      bootstrapAttempted.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
// console.log("Bootstrap hook mounted");
// import {  useEffect } from "react";
// import { accountService } from "@shared/api";
// import { setAuthToken } from "@shared/lib";
// import { useAuthStore } from "@entities/user";

// // Module-level — survives StrictMode remounts, resets on true page reload
// let bootstrapAttempted = false

// export function useBootstrapAuth() {
//   console.log('use bootsrat ma hu ab restore method ki targ ja ra hu ')
//   // const [isBootstrapping, setIsBootstrapping] = useState(true);
//   const setBootstrapping = useAuthStore((state) => state.setBootstrapping);
//   const setUser = useAuthStore((state) => state.setUser);
//   const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

//   console.log("isAuthenticated =", isAuthenticated);

//   useEffect(() => {
//     console.log("Effect running");

//     // Already authenticated in this session — skip immediately
//     if (isAuthenticated) {
//       setBootstrapping(false);
//       return;
//     }

//     // User explicitly logged out — do not restore session
//     if (sessionStorage.getItem("logged_out") === "true") {
//       setBootstrapping(false);
//       return;
//     }

//     // Strict Mode double mount guard
//     if (bootstrapAttempted) return;
//     bootstrapAttempted = true;

//     const restore = async () => {
//       console.log("ma restore ma agya hu")
//       try {
//         console.log('try kar ra hu')
//         const refreshResult = await accountService.bootstrap();
//         const newAccessToken = refreshResult?.data?.access;

//         if (!newAccessToken) {
//           // Bootstrap responded but no token — cookie was invalid
//           setBootstrapping(false);
//           return;
//         }

//         setAuthToken(newAccessToken);

//         // Fetch full profile to populate Zustand store
//         const profileResult = await accountService.getProfile();
//         setUser(profileResult.data);
//       } catch {
//         console.log('try to huva ni catch ma agay hu')
//         // No cookie, expired cookie, or network error
//         // All are silent — user will see login page via ProtectedRoute
//       } finally {
//         setBootstrapping(false);
//       }
//     };

//     restore();
//   // eslint-disable-next-line react-hooks/exhaustive-deps
//   }, []);

// }
