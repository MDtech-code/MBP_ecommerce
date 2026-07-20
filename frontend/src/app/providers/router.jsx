// src/app/providers/router.jsx
import { createBrowserRouter, Outlet } from "react-router-dom"
import { MainLayout }      from "../layouts"
import { DashboardLayout } from "../layouts"

import { HomePage }                  from "@pages/home"
import { RegisterPage }              from "@pages/register"
import { LoginPage }                 from "@pages/login"
import { VerifyEmailPage,
         ForgotPasswordPage,
         ForgotPasswordSentPage,
         ResetPasswordPage }         from "@pages/auth"
import { ProfilePage }               from "@pages/profile"
import { ProductListingPage,
         ProductDetailPage }         from "@pages/products"
import { CartPage }                  from "@pages/cart"
import { SecurityPage,
         ChangePasswordPage,DeleteAccountPage, SecurityVerificationGatePage,
  OTPEntryPage,
  ChangeEmailFormPage,
  NewEmailOTPPage, }        from "@pages/security"



import ProtectedRoute from "./guards/ProtectedRoute"
import GuestRoute     from "./guards/GuestRoute"



export const router = createBrowserRouter([

  // ── Public routes — MainLayout provides Header + Footer ────────
  {
    element: (
      <MainLayout>
        <Outlet />
      </MainLayout>
    ),
    children: [
      { path: "/",              element: <HomePage /> },
      { path: "/product",       element: <ProductListingPage /> },
      { path: "/product/:slug", element: <ProductDetailPage /> },
    ],
  },

  // ── Auth routes — GuestRoute guard ─────────────────────────────
  // No layout here — each auth page wraps itself in AuthLayout
  // because each needs different brandProps
  {
    element: <GuestRoute />,
    children: [
      { path: "/register",             element: <RegisterPage /> },
      { path: "/login",                element: <LoginPage /> },
      { path: "/verify-email",         element: <VerifyEmailPage /> },
      { path: "/forgot-password",      element: <ForgotPasswordPage /> },
      { path: "/forgot-password/sent", element: <ForgotPasswordSentPage /> },
      { path: "/reset-password",       element: <ResetPasswordPage /> },
    ],
  },
   {
  element: <ProtectedRoute />,
  children: [
    {
      element: (
        <MainLayout>
          <Outlet />
        </MainLayout>
      ),
      children: [
        { path: "/cart", element: <CartPage /> },
        
      ],
    },
  ],
},

  // ── Protected routes — nested pattern ─────────────────────────
  //
  // WHY NESTED:
  //   ProtectedRoute renders <Outlet /> internally.
  //   If we pass DashboardLayout as children to ProtectedRoute
  //   it gets ignored — ProtectedRoute never renders children prop.
  //
  // SOLUTION:
  //   Level 1: ProtectedRoute — handles auth check
  //            renders <Outlet /> if authenticated
  //   Level 2: DashboardLayout — handles layout
  //            renders <Outlet /> for actual pages
  //   Level 3: Actual pages — pure content only
  //
  // FLOW for /cart:
  //   ProtectedRoute checks auth → passes → renders Outlet
  //   Outlet hits DashboardLayout route → renders Header+Sidebar+Outlet
  //   Outlet hits CartPage → renders cart content
  //
  {
    element: <ProtectedRoute />,        // Level 1 — auth check
    children: [
      {
        element: (                      // Level 2 — layout
          <DashboardLayout>
            <Outlet />
          </DashboardLayout>
        ),
        children: [                     // Level 3 — pages
          { path: "/profile",                  element: <ProfilePage /> },
           // ── Security section ─────────────────────────────────────────────
          { path: "/security",                        element: <SecurityPage /> },

          // Step 1 — Gate (choose verification method)
          { path: "/security/verify",                 element: <SecurityVerificationGatePage /> },

          // Step 2 — OTP entry (identity verification on current email)
          { path: "/security/verify-otp",             element: <OTPEntryPage /> },

          // Step 3a — Change password form (after identity verified)
          { path: "/security/change-password",        element: <ChangePasswordPage /> },

          // Step 3b — Change email: enter new address (after identity verified)
          { path: "/security/change-email/new",       element: <ChangeEmailFormPage /> },

          // Step 3c — Delete account confirmation (after identity verified)
          { path: "/security/delete-account/confirm", element: <DeleteAccountPage /> },

          // Step 4 — New email OTP (confirm ownership of new address)
          { path: "/security/verify-new-email-otp",   element: <NewEmailOTPPage /> },
        ],
      },
    ],
  },

])
// // src/routes/index.jsx
// // Only change: add ProtectedRoute wrapper for /profile

// import { createBrowserRouter } from "react-router-dom"

// import { HomePage as Home } from "@pages/home"
// import { RegisterPage as Register } from "@pages/register"
// import { LoginPage as Login } from "@pages/login"
// import { VerifyEmailPage as VerifyEmail } from "@pages/auth"
// import { ForgotPasswordPage as ForgotPassword } from "@pages/auth"
// import { ResetPasswordPage as ResetPassword } from "@pages/auth"
// import { ProfilePage as Profile } from "@pages/profile"
// import { ProductListingPage as ProductListing } from "@pages/products"
// import { ProductDetailPage as ProductDetail } from "@pages/products"
// import { CartPage } from "@pages/cart"
// import { SecurityPage as Security } from "@pages/security";
// import { ChangePasswordPage as ChangePassword } from "@pages/security";
// import { ForgotPasswordSentPage as ForgotPasswordSent } from "@pages/auth";


// import ProtectedRoute from "../providers/guards/ProtectedRoute"
// import GuestRoute from "../providers/guards/GuestRoute";

// export const router = createBrowserRouter([
//   { path: "/",               element: <Home /> },
//   { path: "/product",        element: <ProductListing /> },
//   { path: "/product/:slug", element: <ProductDetail /> },

 
//   // GEST - must be attept by non authenticated user 
//   {
//     element:<GuestRoute/>,
//     children:[
//   { path: "/register",       element: <Register /> },
//   { path: "/login",          element: <Login /> },
//   { path: "/verify-email",   element: <VerifyEmail /> },
//   { path: "/forgot-password",element: <ForgotPassword /> },
//    { path: "/forgot-password/sent", element: <ForgotPasswordSent /> },
//   { path: "/reset-password", element: <ResetPassword /> },

//     ]
//   },

//   // Protected — must be authenticated
//   {
//     element: <ProtectedRoute />,
//     children: [
//       { path: "/profile", element: <Profile /> },
//       { path: "/cart",    element: <CartPage /> },

//       { path: "/security", element: <Security /> },
//       {path: "/security/change-password",element: <ChangePassword />},
//     ],
//   },
// ])