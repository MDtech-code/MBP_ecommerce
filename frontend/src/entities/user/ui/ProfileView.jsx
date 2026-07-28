// src/entities/ui/ProfileView.jsx
import { UserRound, Camera, Mail, Phone, MapPin, Calendar, Venus, Edit3 , ShieldAlert, ShieldCheck} from "lucide-react"
import ProfileInfoRow from "./ProfileInfoRow"
import { getMediaUrl } from "@shared/lib"

export default function ProfileView({ user, onEdit, onAvatarClick , onManageAddresses}) {
  // Address now comes from user.addresses — not user.profile
  const defaultAddress = user?.default_address || null

  return (
    <div className="space-y-6">

      {/* Top Card */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">

          {/* Avatar with camera button */}
          <div className="relative shrink-0">
            <div className="w-24 h-24 rounded-2xl bg-gray-100 overflow-hidden border border-gray-200 flex items-center justify-center">
              {user?.profile?.avatar ? (
                <img
                  src={getMediaUrl(user.profile.avatar)}
                  alt={user?.full_name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <UserRound size={48} className="text-gray-300" />
              )}
            </div>
            <button
              onClick={onAvatarClick}
              className="absolute -bottom-2 -right-2 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center shadow-md hover:opacity-90 transition-opacity"
            >
              <Camera size={13} />
            </button>
          </div>

          {/* Name + badges */}
          <div className="flex-1 text-center sm:text-left">
            <h2 className="text-2xl font-black text-gray-900">
              {user?.full_name || "—"}
            </h2>
            <p className="text-gray-400 text-sm mt-1">{user?.email}</p>
            <div className="flex items-center justify-center sm:justify-start gap-2 mt-3">
              <span className="bg-primary/10 text-primary text-xs font-bold px-3 py-1 rounded-full">
                {user?.role_display || "Customer"}
              </span>
              {user?.is_verified && (
                <span className="bg-green-50 text-green-600 text-xs font-bold px-3 py-1 rounded-full">
                  Verified
                </span>
              )}
            </div>
          </div>

          {/* Edit button */}
          <button
            onClick={onEdit}
            className="flex items-center gap-2 border border-primary text-primary px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:bg-primary hover:text-white transition-all shrink-0"
          >
            <Edit3 size={14} />
            EDIT PROFILE
          </button>

        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Personal */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide mb-4">
            Personal Information
          </h3>
          <ProfileInfoRow icon={Mail}     label="Email"         value={user?.email} />
          {/* Replace the existing phone row with this */}
<div className="flex items-center justify-between">
  <ProfileInfoRow
    icon={Phone}
    label="Phone"
    value={user?.profile?.phone}
  />
  {user?.profile?.phone && (
    user?.profile?.is_phone_verified ? (
      <span className="flex items-center gap-1 text-green-600 text-xs font-bold">
        <ShieldCheck size={13} /> Verified
      </span>
    ) : (
      <span className="flex items-center gap-1 text-amber-500 text-xs font-bold">
        <ShieldAlert size={13} /> Not verified
      </span>
    )
  )}
</div>
          {/* <ProfileInfoRow icon={Phone}    label="Phone"         value={user?.profile?.phone} /> */}
          <ProfileInfoRow icon={Calendar} label="Date of Birth" value={user?.profile?.date_of_birth} />
          <ProfileInfoRow icon={Venus}    label="Gender"        value={user?.profile?.gender_display} />
        </div>

        {/* Address */}
                {/* Address — now from default_address not profile */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide">
              Default Address
            </h3>
            <button
              onClick={onManageAddresses}
              className="text-xs font-bold text-primary hover:underline"
            >
              Manage Addresses
            </button>
          </div>

          {defaultAddress ? (
            <>
              <ProfileInfoRow icon={MapPin} label="Label"          value={defaultAddress?.label_display} />
              <ProfileInfoRow icon={MapPin} label="Address Line 1" value={defaultAddress?.address_line1} />
              <ProfileInfoRow icon={MapPin} label="Address Line 2" value={defaultAddress?.address_line2} />
              <ProfileInfoRow icon={MapPin} label="City"           value={defaultAddress?.city} />
              <ProfileInfoRow icon={MapPin} label="Province"       value={defaultAddress?.province_display} />
              <ProfileInfoRow icon={MapPin} label="Postal Code"    value={defaultAddress?.postal_code} />
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-6 gap-2">
              <MapPin size={24} className="text-gray-200" />
              <p className="text-sm text-gray-400">No address added yet.</p>
              <button
                onClick={onManageAddresses}
                className="text-xs font-bold text-primary hover:underline mt-1"
              >
                Add your first address
              </button>
            </div>
          )}
        </div>
       

      </div>

        {/* Full Address Banner — from default_address */}
      {defaultAddress?.full_address && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
            <MapPin size={16} className="text-primary" />
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
              Full Address
            </p>
            <p className="text-sm font-semibold text-gray-800 mt-0.5">
              {defaultAddress.full_address}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}