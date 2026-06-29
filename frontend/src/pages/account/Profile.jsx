import { UserRound, Camera } from "lucide-react";
import DashboardLayout from "../../components/account/DashboardLayout";

const profile = {
  full_name: "John Rider",
  email: "rider@example.com",
  phone: "0312 3456789",
  address: "Lahore, Punjab, Pakistan",
};

export default function Profile() {
  return (
    <DashboardLayout>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 lg:p-8">

        {/* Header Row */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-black text-gray-900">
              Profile Information
            </h1>
            <p className="text-gray-400 text-sm mt-1">
              Manage your personal information
            </p>
          </div>

          <button className="border border-primary text-primary px-5 py-2 rounded-md font-bold text-xs tracking-wide hover:bg-red-50 transition">
            EDIT PROFILE
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-col lg:flex-row gap-8">

          {/* Left - Avatar */}
          <div className="flex flex-col items-center lg:w-56 shrink-0">

            <div className="w-32 h-32 rounded-full bg-gray-100 flex items-center justify-center overflow-hidden">
              <UserRound size={70} className="text-gray-300" />
            </div>

            <h2 className="mt-4 font-black text-lg text-gray-900">
              {profile.full_name}
            </h2>

            <p className="text-gray-400 text-sm mt-1">
              {profile.email}
            </p>

            <p className="text-gray-600 text-sm font-medium mt-2">
              {profile.phone}
            </p>

            <p className="text-gray-400 text-sm mt-1">
              Lahore, Pakistan
            </p>

            <button className="mt-5 border border-primary text-primary px-5 py-2 rounded-md font-bold text-xs tracking-wide flex items-center gap-2 hover:bg-red-50 transition">
              <Camera size={15} />
              CHANGE PHOTO
            </button>

          </div>

          {/* Subtle Divider */}
          <div className="hidden lg:block w-px bg-gray-100 self-stretch" />

          {/* Right - Form */}
          <div className="flex-1 space-y-5">

            <ProfileInput label="Full Name" value={profile.full_name} />
            <ProfileInput label="Email Address" value={profile.email} />
            <ProfileInput label="Phone Number" value={profile.phone} />
            <ProfileInput label="Address" value={profile.address} />

            <div className="flex justify-end pt-4">
              <button className="bg-primary text-white px-10 py-3 rounded-md font-bold text-sm tracking-wide hover:bg-red-700 transition">
                SAVE CHANGES
              </button>
            </div>

          </div>

        </div>

      </div>

    </DashboardLayout>
  );
}

function ProfileInput({ label, value }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-600 mb-1.5">
        {label}
      </label>
      <input
        value={value}
        readOnly
        className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm outline-none bg-white text-gray-700"
      />
    </div>
  );
}