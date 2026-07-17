// src/routes/index.jsx
// Only change: add ProtectedRoute wrapper for /profile

import { createBrowserRouter } from "react-router-dom"

import { HomePage as Home } from "@pages/home"
import { RegisterPage as Register } from "@pages/register"
import { LoginPage as Login } from "@pages/login"
import { VerifyEmailPage as VerifyEmail } from "@pages/auth"
import { ForgotPasswordPage as ForgotPassword } from "@pages/auth"
import { ResetPasswordPage as ResetPassword } from "@pages/auth"
import { ProfilePage as Profile } from "@pages/profile"
import { ProductListingPage as ProductListing } from "@pages/products"
import { ProductDetailPage as ProductDetail } from "@pages/products"
import { CartPage } from "@pages/cart"
import { SecurityPage as Security } from "@pages/security";
import { ChangePasswordPage as ChangePassword } from "@pages/security";
import { ForgotPasswordSentPage as ForgotPasswordSent } from "@pages/auth";


import ProtectedRoute from "../providers/guards/ProtectedRoute"
import GuestRoute from "../providers/guards/GuestRoute";

export const router = createBrowserRouter([
  { path: "/",               element: <Home /> },
  { path: "/product",        element: <ProductListing /> },
  { path: "/product/:slug", element: <ProductDetail /> },

 
  // GEST - must be attept by non authenticated user 
  {
    element:<GuestRoute/>,
    children:[
  { path: "/register",       element: <Register /> },
  { path: "/login",          element: <Login /> },
  { path: "/verify-email",   element: <VerifyEmail /> },
  { path: "/forgot-password",element: <ForgotPassword /> },
   { path: "/forgot-password/sent", element: <ForgotPasswordSent /> },
  { path: "/reset-password", element: <ResetPassword /> },

    ]
  },

  // Protected — must be authenticated
  {
    element: <ProtectedRoute />,
    children: [
      { path: "/profile", element: <Profile /> },
      { path: "/cart",    element: <CartPage /> },

      { path: "/security", element: <Security /> },
      {path: "/security/change-password",element: <ChangePassword />},
    ],
  },
])