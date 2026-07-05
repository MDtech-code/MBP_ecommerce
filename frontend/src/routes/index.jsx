// src/routes/index.jsx
// Only change: add ProtectedRoute wrapper for /profile

import { createBrowserRouter } from "react-router-dom"
import Home from "../pages/Home"
import TestintegrationPage from "../pages/TestIntegrationPage"
import Register from "../pages/account/Register"
import Login from "../pages/account/Login"
import VerifyEmail from "../pages/account/VerifyEmail"
import ForgotPassword from "../pages/account/ForgotPassword"
import ResetPassword from "../pages/account/ResetPassword"
import Profile from "../pages/account/Profile"
import ProductListing from "../pages/products/ProductListing"
import ProductDetail from "../pages/products/ProductDetail"
import CartPage from "../pages/cart/CartPage"
import ProtectedRoute from "../components/layout/ProtectedRoute"
import Security from "../pages/account/security/Security";
import ChangePassword from "../pages/account/security/ChangePassword";
import ForgotPasswordSent from "../pages/account/ForgotPasswordSent";

export const router = createBrowserRouter([
  { path: "/",               element: <Home /> },
  { path: "/testapp",        element: <TestintegrationPage /> },
  { path: "/register",       element: <Register /> },
  { path: "/login",          element: <Login /> },
  { path: "/verify-email",   element: <VerifyEmail /> },
  { path: "/forgot-password",element: <ForgotPassword /> },
  { path: "/reset-password", element: <ResetPassword /> },
  { path: "/product",        element: <ProductListing /> },
  { path: "/product-detail", element: <ProductDetail /> },
  { path: "/cart",           element: <CartPage /> },
  { path: "/forgot-password", element: <ForgotPassword /> },
  // Confirmation screen shown after reset email is sent
  { path: "/forgot-password/sent", element: <ForgotPasswordSent /> },

  { path: "/reset-password",  element: <ResetPassword /> },

  // Protected — must be authenticated
  {
    element: <ProtectedRoute />,
    children: [
      { path: "/profile", element: <Profile /> },
      { path: "/security", element: <Security /> },
      {path: "/security/change-password",element: <ChangePassword />},
    ],
  },
])