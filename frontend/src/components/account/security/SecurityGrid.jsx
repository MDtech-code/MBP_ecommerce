import {
  Lock,
  Smartphone,
  ShieldCheck,
  Trash2,
} from "lucide-react";

import { useNavigate } from "react-router-dom";

import SecurityCard from "./SecurityCard";

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
        onClick={() => navigate("/security/change-password")}
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
        description="Permanently delete your BikeExpress account."
        status="Coming Soon"
        statusColor="bg-gray-100 text-gray-600"
        actionText="Coming Soon"
        disabled
      />

    </div>

  );
}