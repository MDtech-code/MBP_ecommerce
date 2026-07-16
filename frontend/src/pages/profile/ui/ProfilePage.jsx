// src/pages/account/Profile.jsx

import { useState } from "react"
import DashboardLayout from "../../../widgets/layout/ui/DashboardLayout"
import ProfileView from "../../../entities/user/ui/ProfileView"
import ProfileEditForm from "../../../features/profile/ui/ProfileEditForm"
import AvatarModal from "../../../features/profile/ui/AvatarModal"
import AddressManager from "../../../widgets/profile/ui/AddressManager"
import { useAuthStore } from "@entities/user"
import { useProfile } from "../../../features/profile/api/useProfileMutations"
import { hasAuthToken } from "../../../shared/lib/authToken"

// src/pages/account/Profile.jsx

export default function Profile() {
  const user = useAuthStore((state) => state.user)
  const [mode, setMode] = useState("view")
  const [showAvatarModal, setShowAvatarModal] = useState(false)

  const { isLoading } = useProfile({
    enabled: hasAuthToken() || !user,
  })

  if (isLoading && !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <span className="loading loading-spinner loading-md text-primary" />
        </div>
      </DashboardLayout>
    )
  }

  const renderContent = () => {
    if (mode === "edit") {
      return <ProfileEditForm onCancel={() => setMode("view")} />
    }

    if (mode === "addresses") {
      return <AddressManager onBack={() => setMode("view")} />
    }

    return (
      <ProfileView
        user={user}
        onEdit={() => setMode("edit")}
        onAvatarClick={() => setShowAvatarModal(true)}
        onManageAddresses={() => setMode("addresses")}
      />
    )
  }

  return (
    <DashboardLayout>

      {renderContent()}

      {showAvatarModal && (
        <AvatarModal
          currentAvatar={user?.profile?.avatar}
          onClose={() => setShowAvatarModal(false)}
        />
      )}

    </DashboardLayout>
  )
}
