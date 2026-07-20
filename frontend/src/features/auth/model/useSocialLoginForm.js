// src/features/auth/model/useSocialLoginForm.js

import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@entities/user";
import { useSocialLogin } from "../api/useAuthMutations";
import { normalizeError } from "@shared/api";

/**
 * Encapsulates all social login business logic.
 *
 * Responsibilities:
 *   - Receive token from provider callback
 *   - Call backend social auth endpoint
 *   - Store access token on success
 *   - Navigate to home on success
 *   - Return error state to UI
 *
 * UI component stays dumb — only renders what this hook returns.
 */
export function useSocialLoginForm() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const {
    mutate: socialLogin,
    isPending,
    isError,
    error,
    reset,
  } = useSocialLogin();

  const normalized = isError ? normalizeError(error) : null;

  // Non-field error — provider unreachable, token invalid, account inactive
  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;

  /**
   * Called by Google or Facebook button after they receive their token.
   *
   * @param {"google" | "facebook"} provider
   * @param {string}                token    — ID token or access token
   */
  const handleSocialAuth = (provider, token) => {
    // Clear previous error before new attempt
    reset();

    socialLogin(
      { provider, token },
      {
        onSuccess: (data) => {
            console.log(data)
          // access token in response body
          // refresh token already in HttpOnly cookie (set by backend)
          login({ access: data.data.access, user: data.data.user });
          navigate("/");
        },
      },
    );
  };

  return {
    handleSocialAuth,
    isPending,
    formError,
    formErrorCode,
  };
}
