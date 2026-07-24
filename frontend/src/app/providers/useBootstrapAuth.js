import { useEffect } from "react";
import { accountService } from "@shared/api";
import { setAuthToken } from "@shared/lib";
import { useAuthStore } from "@entities/user";

// Store the promise instead of a boolean
let bootstrapPromise = null;

export function useBootstrapAuth() {
  const setBootstrapping = useAuthStore((state) => state.setBootstrapping);
  const setUser = useAuthStore((state) => state.setUser);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (isAuthenticated) {
      setBootstrapping(false);
      return;
    }

    // if (sessionStorage.getItem("logged_out") === "true") {
    //   setBootstrapping(false);
    //   return;
    // }
    if (sessionStorage.getItem("logged_out") === "true") {
      setBootstrapping(false);
      return;
    }

    // HMR / Strict Mode Guard:
    // If a request is already in flight (or finished), just attach to it
    if (bootstrapPromise) {
      bootstrapPromise.finally(() => setBootstrapping(false));
      return;
    }

    const restore = async () => {
      try {
        const refreshResult = await accountService.bootstrap();
        const newAccessToken = refreshResult?.data?.access;

        if (!newAccessToken) return;

        setAuthToken(newAccessToken);
        const profileResult = await accountService.getProfile();
        setUser(profileResult.data);
      } catch {
        // Silent failure — user stays unauthenticated
      }
    };

    // Assign the promise to the module variable
    bootstrapPromise = restore();

    // Ensure the loading state clears when the promise resolves
    bootstrapPromise.finally(() => {
      setBootstrapping(false);
    });

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
