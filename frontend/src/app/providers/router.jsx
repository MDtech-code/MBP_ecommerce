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

// Pages — Protected (no sidebar)
import { CartPage }                   from "@pages/cart"

// Pages — Dashboard (sidebar)
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
  // Completely separate from RootLayout
  // Has its own full-screen AuthLayout (no Header/Footer)
  // GuestRoute redirects authenticated users to /
  {
    element: <GuestRoute />,
    children: [
      {
        element: <AuthLayout />,
        children: [
          { path: "/login",                element: <LoginPage /> },
          { path: "/register",             element: <RegisterPage /> },
          { path: "/forgot-password",      element: <ForgotPasswordPage /> },
          { path: "/forgot-password/sent", element: <ForgotPasswordSentPage /> },
          { path: "/reset-password",       element: <ResetPasswordPage /> },
        ],
      },
    ],
  },

  // ── 2. VERIFY EMAIL — outside GuestRoute ───────────────────────
  // User may click email link while already logged in
  // So this sits outside GuestRoute guard
  // Still uses AuthLayout for consistent visual
  {
    element: <AuthLayout />,
    children: [
      { path: "/verify-email", element: <VerifyEmailPage /> },
    ],
  },

  // ── 3. MAIN APP — RootLayout owns Header + Footer ──────────────
  // Header and Footer mount ONCE here
  // All standard pages live inside this shell
  {
    element: <RootLayout />,
    children: [

      // ── 3a. Public pages — no auth required ──────────────────
      { path: "/",              element: <HomePage /> },
      { path: "/product",       element: <ProductListingPage /> },
      { path: "/product/:slug", element: <ProductDetailPage /> },

      // ── 3b. Protected — no sidebar (cart, checkout etc) ──────
      // Has Header + Footer from RootLayout
      // No sidebar — feels like store, not dashboard
      {
        element: <ProtectedRoute />,
        children: [
          { path: "/cart", element: <CartPage /> },
        ],
      },

      // ── 3c. Protected — dashboard (has sidebar) ───────────────
      // Has Header + Footer from RootLayout
      // DashboardLayout adds sidebar only
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









// // src/app/providers/router.jsx
// import { createBrowserRouter } from "react-router-dom"
// import { MainLayout }      from "../layouts"
// import { DashboardLayout } from "../layouts"
// import {AuthLayout}  from "../layouts"

// import { HomePage }                  from "@pages/home"
// import { RegisterPage }              from "@pages/register"
// import { LoginPage }                 from "@pages/login"
// import { VerifyEmailPage,
//          ForgotPasswordPage,
//          ForgotPasswordSentPage,
//          ResetPasswordPage }         from "@pages/auth"
// import { ProfilePage }               from "@pages/profile"
// import { ProductListingPage,
//          ProductDetailPage }         from "@pages/products"
// import { CartPage }                  from "@pages/cart"
// import { SecurityPage,
//          ChangePasswordPage,DeleteAccountPage, SecurityVerificationGatePage,
//   OTPEntryPage,
//   ChangeEmailFormPage,
//   NewEmailOTPPage, }        from "@pages/security"



// import ProtectedRoute from "./guards/ProtectedRoute"
// import GuestRoute     from "./guards/GuestRoute"



// export const router = createBrowserRouter([

//   // ── Public routes — MainLayout provides Header + Footer ────────
//   {
//     element: <MainLayout />,
//     children: [
//       { path: "/",              element: <HomePage /> },
//       { path: "/product",       element: <ProductListingPage /> },
//       { path: "/product/:slug", element: <ProductDetailPage /> },
//     ],
//   },

//   // ── Auth routes — GuestRoute guard ─────────────────────────────
//   // No layout here — each auth page wraps itself in AuthLayout
//   // because each needs different brandProps
//   {
//     element: <GuestRoute />,
//     children: [
//     {
//       element: <AuthLayout />, 
//       children: [
//       { path: "/register",             element: <RegisterPage /> },
//       { path: "/login",                element: <LoginPage /> },
//       { path: "/verify-email",         element: <VerifyEmailPage /> },
//       { path: "/forgot-password",      element: <ForgotPasswordPage /> },
//       { path: "/forgot-password/sent", element: <ForgotPasswordSentPage /> },
//       { path: "/reset-password",       element: <ResetPasswordPage /> },
//     ],
      
//     },
//   ],
    
//   },
//   {
//   element: <ProtectedRoute />,
//   children: [
//     {
//       element: <MainLayout />, 
//       children: [
//         { path: "/cart", element: <CartPage /> },
        
//       ],
//     },
//   ],
// },

//   // ── Protected routes — nested pattern ─────────────────────────
//   //
//   // WHY NESTED:
//   //   ProtectedRoute renders <Outlet /> internally.
//   //   If we pass DashboardLayout as children to ProtectedRoute
//   //   it gets ignored — ProtectedRoute never renders children prop.
//   //
//   // SOLUTION:
//   //   Level 1: ProtectedRoute — handles auth check
//   //            renders <Outlet /> if authenticated
//   //   Level 2: DashboardLayout — handles layout
//   //            renders <Outlet /> for actual pages
//   //   Level 3: Actual pages — pure content only
//   //
//   // FLOW for /cart:
//   //   ProtectedRoute checks auth → passes → renders Outlet
//   //   Outlet hits DashboardLayout route → renders Header+Sidebar+Outlet
//   //   Outlet hits CartPage → renders cart content
//   //
//   {
//     element: <ProtectedRoute />,        // Level 1 — auth check
//     children: [
//       {
//         element: <DashboardLayout />,
//         children: [                     // Level 3 — pages
//           { path: "/profile",                  element: <ProfilePage /> },
//            // ── Security section ─────────────────────────────────────────────
//           { path: "/security",                        element: <SecurityPage /> },

//           // Step 1 — Gate (choose verification method)
//           { path: "/security/verify",                 element: <SecurityVerificationGatePage /> },

//           // Step 2 — OTP entry (identity verification on current email)
//           { path: "/security/verify-otp",             element: <OTPEntryPage /> },

//           // Step 3a — Change password form (after identity verified)
//           { path: "/security/change-password",        element: <ChangePasswordPage /> },

//           // Step 3b — Change email: enter new address (after identity verified)
//           { path: "/security/change-email/new",       element: <ChangeEmailFormPage /> },

          
//           { path: "/security/delete-account/confirm", element: <DeleteAccountPage /> },

          
//           { path: "/security/verify-new-email-otp",   element: <NewEmailOTPPage /> },
//         ],
//       },
//     ],
//   },

// ])

