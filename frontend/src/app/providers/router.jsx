// src/routes/index.jsx
// Only change: add ProtectedRoute wrapper for /profile

import { createBrowserRouter } from "react-router-dom"

import Home from "../../pages/home/ui/HomePage"
import Register from "../../pages/register/ui/RegisterPage"
import Login from "../../pages/login/ui/LoginPage"
import VerifyEmail from "../../pages/auth/ui/VerifyEmailPage"
import ForgotPassword from "../../pages/auth/ui/ForgotPasswordPage"
import ResetPassword from "../../pages/auth/ui/ResetPasswordPage"
import Profile from "../../pages/profile/ui/ProfilePage"
import ProductListing from "../../pages/products/ui/ProductListingPage"
import ProductDetail from "../../pages/products/ui/ProductDetailPage"
import CartPage from "../../pages/cart/ui/CartPage"
import Security from "../../pages/security/ui/SecurityPage";
import ChangePassword from "../../pages/security/ui/ChangePasswordPage";
import ForgotPasswordSent from "../../pages/auth/ui/ForgotPasswordSentPage";


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