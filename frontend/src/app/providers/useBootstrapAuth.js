
import { useEffect } from "react";
import { accountService } from "@shared/api";
import { setAuthToken } from "@shared/lib";
import { useAuthStore } from "@entities/user";
import { clearAuth } from "@shared/lib";

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

    if (sessionStorage.getItem("logged_out") === "true") {
      setBootstrapping(false);
      return;
    }

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
        try {
          const profileResult = await accountService.getProfile();
          setUser(profileResult.data);
        } catch {
          clearAuth();
        }
      } catch {
        // Silent failure — user stays unauthenticated
      }
    };

    bootstrapPromise = restore();

    bootstrapPromise.finally(() => {
      setBootstrapping(false);
    });

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
