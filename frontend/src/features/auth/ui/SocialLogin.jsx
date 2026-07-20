// src/features/auth/ui/SocialLogin.jsx

import { FcGoogle }       from "react-icons/fc";
import { FaFacebookF }    from "react-icons/fa";
import { useGoogleLogin } from "@react-oauth/google";
import { useSocialLoginForm } from "../model/useSocialLoginForm";
import { useEffect } from "react";

export default function SocialLogin() {
  const { handleSocialAuth, isPending, formError } = useSocialLoginForm();

  // ── Load Facebook SDK manually ──────────────────────────────────────────
  useEffect(() => {
    window.fbAsyncInit = function () {
      window.FB.init({
        appId: import.meta.env.VITE_FACEBOOK_APP_ID,
        cookie: true,
        xfbml: true,
        version: "v19.0",
      });
    };

    // Load SDK script only once
    if (!document.getElementById("facebook-jssdk")) {
      const script = document.createElement("script");
      script.id = "facebook-jssdk";
      script.src = "https://connect.facebook.net/en_US/sdk.js";
      document.body.appendChild(script);
    }
  }, []);

  // ── Google ──────────────────────────────────────────────────────────────
  const googleLogin = useGoogleLogin({
    onSuccess: (tokenResponse) => {
      handleSocialAuth("google", tokenResponse.access_token);
    },
    onError: () => console.warn("Google login cancelled or failed"),
    scope: "openid email profile",
  });

  // ── Facebook ─────────────────────────────────────────────────────────────
  const handleFacebookClick = () => {
    window.FB.login(
      (response) => {
        if (response.authResponse) {
          handleSocialAuth("facebook", response.authResponse.accessToken);
        } else {
          console.warn("Facebook login cancelled or failed");
        }
      },
      { scope: "public_profile,email" }
    );
  };

  return (
    <div className="mt-6">

      {/* Divider */}
      <div className="flex items-center gap-3 text-gray-400 text-sm">
        <span className="h-px bg-gray-200 flex-1" />
        OR CONTINUE WITH
        <span className="h-px bg-gray-200 flex-1" />
      </div>

      {/* Backend error */}
      {formError && (
        <div
          role="alert"
          className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2"
        >
          {formError}
        </div>
      )}

      {/* Buttons */}
      <div className="grid grid-cols-2 gap-3 mt-5">

        {/* Google */}
        <button
          type="button"
          disabled={isPending}
          onClick={() => googleLogin()}
          className="flex items-center justify-center gap-2 border rounded-lg py-3 font-semibold hover:bg-gray-50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <FcGoogle size={20} />
          Google
        </button>

        {/* Facebook */}
        <button
          type="button"
          disabled={isPending}
          onClick={handleFacebookClick}
          className="flex items-center justify-center gap-2 border rounded-lg py-3 font-semibold hover:bg-gray-50 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <FaFacebookF size={20} className="text-blue-600" />
          Facebook
        </button>

      </div>

      {isPending && (
        <p className="text-center text-sm text-gray-500 mt-3">
          Authenticating...
        </p>
      )}

    </div>
  );
}