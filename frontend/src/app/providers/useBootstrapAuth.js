// src/hooks/account/useBootstrapAuth.js
console.log("Bootstrap hook mounted");
import {  useEffect } from "react";
import { accountService } from "../../shared/api/services/accountService";
import { setAuthToken } from "../../shared/lib/authToken";

import { useAuthStore } from "@entities/user";

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
