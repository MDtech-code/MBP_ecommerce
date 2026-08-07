// src/pages/addresses/AddressesPage.jsx
//
// Addresses are now a proper routed page under DashboardLayout.
// Previously lived as a "mode" inside Profile.jsx — that meant:
//   - No URL ownership (browser back/refresh lost context)
//   - Callbacks threaded 3 levels deep
//   - AddressManager pretending to be a section not a page
//
// Now: /addresses is its own route. AddressManager renders directly
// here with no onBack prop — navigation is handled by sidebar/browser.

import { AddressManager } from "@widgets/profile"

export default function AddressesPage() {
  return <AddressManager />
}