// src/pages/account/Profile.jsx

import { useState } from "react"
import DashboardLayout from "../../components/account/DashboardLayout"
import ProfileView from "../../components/account/profile/ProfileView"
import ProfileEditForm from "../../components/account/profile/ProfileEditForm"
import AvatarModal from "../../components/account/profile/AvatarModal"
import AddressManager from "../../components/account/profile/AddressManager"
import { useAuthStore } from "../../stores/authStore"
import { useProfile } from "../../hooks/account/useAuthMutations"
import { hasAuthToken } from "../../api/auth"

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
