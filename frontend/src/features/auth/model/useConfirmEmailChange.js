// src/features/auth/model/useConfirmEmailChange.js

import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useConfirmEmailChange as useConfirmMutation } from "../api/useAuthMutations";
import { useAuthStore } from "@entities/user";

/**
 * Email change CONFIRMATION logic.
 *
 * Triggered when user lands on /verify-email-change?token=xxx
 *
 * Flow:
 *   1. Extract token from URL on mount
 *   2. Call confirm endpoint automatically
 *   3. Backend confirms change + blacklists all tokens
 *   4. Frontend clears auth state (logout)
 *   5. Navigate to /login with success message
 *
 * Why logout here and not on request:
 *   Backend only blacklists tokens AFTER confirmation.
 *   Logging out on request would kick the user out
 *   before their session is actually invalid.
 *   Logging out here matches the exact moment
 *   the backend invalidates the session.
 *
 * Route must be PUBLIC — user may or may not be logged in
 * when they click the email link.
 * Token itself is the authentication for this action.
 */
export function useConfirmEmailChangeForm() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const [searchParams] = useSearchParams();

  const {
    mutate: confirm,
    isPending,
    isError,
    isSuccess,
    error,
  } = useConfirmMutation();

  const token = searchParams.get("token");

  // Auto-trigger on mount — user just clicked the email link
  useEffect(() => {
    if (!token) return;
    confirm(
      { token },
      {
        onSuccess: () => {
          // Backend confirmed + blacklisted tokens
          // Clear frontend auth state now — session is invalid
          logout();
          navigate("/login", {
            replace: true,
            state: {
              message:
                "Your email has been updated successfully. Please log in with your new email address.",
            },
          });
        },
      },
    );
  }, [token]);

  return {
    isPending,
    isError,
    isSuccess,
    hasToken: !!token,
  };
}
