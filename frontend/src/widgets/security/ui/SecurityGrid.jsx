// src/widgets/security-grid/ui/SecurityGrid.jsx

import { Lock, Smartphone, ShieldCheck, Trash2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import SecurityCard    from "./SecurityCard";

export default function SecurityGrid() {
  const navigate = useNavigate();

  return (
    <div className="grid gap-6">

      <SecurityCard
        icon={Lock}
        title="Password"
        description="Change your account password to keep your account secure."
        status="Active"
        actionText="Change Password"
        onClick={() => navigate("/security/verify?purpose=change_password")}
      />

      <SecurityCard
        icon={Lock}
        title="Email Address"
        description="Update the email address associated with your account."
        status="Active"
        actionText="Change Email"
        onClick={() => navigate("/security/verify?purpose=change_email")}
      />

      <SecurityCard
        icon={Smartphone}
        title="Active Sessions"
        description="Manage devices currently signed in to your account."
        status="Coming Soon"
        statusColor="bg-gray-100 text-gray-600"
        actionText="Coming Soon"
        disabled
      />

      <SecurityCard
        icon={ShieldCheck}
        title="Two-Factor Authentication"
        description="Add an extra layer of protection to your account."
        status="Coming Soon"
        statusColor="bg-gray-100 text-gray-600"
        actionText="Coming Soon"
        disabled
      />

      <SecurityCard
        icon={Trash2}
        title="Delete Account"
        description="Permanently delete your BikeExpress account and all associated data."
        status="Danger Zone"
        statusColor="bg-red-50 text-red-600"
        actionText="Delete Account"
        onClick={() => navigate("/security/verify?purpose=delete_account")}
      />

    </div>
  );
}
// import {
//   Lock,
//   Smartphone,
//   ShieldCheck,
//   Trash2,
// } from "lucide-react";

// import { useNavigate } from "react-router-dom";

// import SecurityCard from "./SecurityCard";

// export default function SecurityGrid() {

//   const navigate = useNavigate();

//   return (

//     <div className="grid gap-6">

//       <SecurityCard
//         icon={Lock}
//         title="Password"
//         description="Change your account password to keep your account secure."
//         status="Active"
//         actionText="Change Password"
//         onClick={() => navigate("/security/change-password")}
//       />
//       {/* ── Email — now active ──────────────────────────────────────────── */}
//       <SecurityCard
//         icon={Lock}
//         title="Email Address"
//         description="Update your email address. We will send a verification link to the new address."
//         status="Active"
//         actionText="Change Email"
//         onClick={() => navigate("/security/change-email")}
//       />


//       <SecurityCard
//         icon={Smartphone}
//         title="Active Sessions"
//         description="Manage devices currently signed in to your account."
//         status="Coming Soon"
//         statusColor="bg-gray-100 text-gray-600"
//         actionText="Coming Soon"
//         disabled
//       />

//       <SecurityCard
//         icon={ShieldCheck}
//         title="Two-Factor Authentication"
//         description="Add an extra layer of protection to your account."
//         status="Coming Soon"
//         statusColor="bg-gray-100 text-gray-600"
//         actionText="Coming Soon"
//         disabled
//       />

//       <SecurityCard
//         icon={Trash2}
//         title="Delete Account"
//         description="Permanently delete your BikeExpress account and all associated data."
//         status="Danger Zone"
//         statusColor="bg-red-50 text-red-600"
//         actionText="Delete Account"
//         actionColor="text-red-500 border-red-200 hover:bg-red-50"
//         onClick={() => navigate("/security/delete-account")}
//       />

//     </div>

//   );
// }