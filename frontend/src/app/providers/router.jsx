// src/routes/index.jsx
// Only change: add ProtectedRoute wrapper for /profile

import { createBrowserRouter } from "react-router-dom"

import Home from "../pages/Home"
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