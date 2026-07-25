// src/app/providers/router.jsx

import { createBrowserRouter } from "react-router-dom"

// Layouts

import { DashboardLayout } from "../layouts"
import { AuthLayout }      from "../layouts"
import { RootLayout }      from "../layouts"

// Guards
import ProtectedRoute from "./guards/ProtectedRoute"
import GuestRoute     from "./guards/GuestRoute"

// Pages — Public
import { HomePage }                   from "@pages/home"
import { ProductListingPage,
         ProductDetailPage }          from "@pages/products"

// Pages — Auth
import { RegisterPage }               from "@pages/register"
import { LoginPage }                  from "@pages/login"
import { VerifyEmailPage,
         ForgotPasswordPage,
         ForgotPasswordSentPage,
         ResetPasswordPage }          from "@pages/auth"

// Pages — Protected 
import { CartPage }                   from "@pages/cart"

// Pages — Dashboard 
import { ProfilePage }                from "@pages/profile"
import { SecurityPage,
         ChangePasswordPage,
         DeleteAccountPage,
         SecurityVerificationGatePage,
         OTPEntryPage,
         ChangeEmailFormPage,
         NewEmailOTPPage }            from "@pages/security"


export const router = createBrowserRouter([

  // ── 1. GUEST ONLY — Auth Flow ──────────────────────────────────
  // GuestRoute redirects authenticated users to /
  {
    element: <GuestRoute />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: "/login",                element: <LoginPage /> },
          { path: "/register",             element: <RegisterPage /> },
          { path: "/verify-email", element: <VerifyEmailPage /> },
          { path: "/forgot-password",      element: <ForgotPasswordPage /> },
          { path: "/forgot-password/sent", element: <ForgotPasswordSentPage /> },
          { path: "/reset-password",       element: <ResetPasswordPage /> },
        ],
      },
    ],
  },

  

  // ── 3. MAIN APP — RootLayout owns Header + Footer ──────────────
  
  {
    element: <RootLayout />,
    children: [

      // ── 3a. Public pages  ──────────────────
      { path: "/",              element: <HomePage /> },
      { path: "/product",       element: <ProductListingPage /> },
      { path: "/product/:slug", element: <ProductDetailPage /> },

      // ── 3b. Protected  ──────
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/cart", element: <CartPage /> },
        ],
      },

      // ── 3c. Protected — dashboard  ───────────────
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <DashboardLayout />,
            children: [
              { path: "/profile", element: <ProfilePage /> },
              // ── Security hub ────────────────────────────────
              { path: "/security",                        element: <SecurityPage /> },
              { path: "/security/verify",                 element: <SecurityVerificationGatePage /> },
              { path: "/security/verify-otp",             element: <OTPEntryPage /> },
              { path: "/security/change-password",        element: <ChangePasswordPage /> },
              { path: "/security/change-email/new",       element: <ChangeEmailFormPage /> },
              { path: "/security/delete-account/confirm", element: <DeleteAccountPage /> },
              { path: "/security/verify-new-email-otp",   element: <NewEmailOTPPage /> },
            ],
          },
        ],
      },

    ],
  },

])








