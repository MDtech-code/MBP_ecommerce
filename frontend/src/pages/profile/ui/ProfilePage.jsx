// src/pages/account/Profile.jsx

import { useState } from "react"


import { ProfileView } from "@entities/user"
import { ProfileEditForm } from "@features/profile"
import { AvatarModal } from "@features/profile"
import { AddressManager } from "@widgets/profile"
import { useProfile } from "@features/profile"
import { hasAuthToken } from "@shared/lib"

import { useAuthStore } from "@entities/user"


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
      <>
        <div className="flex items-center justify-center h-64">
          <span className="loading loading-spinner loading-md text-primary" />
        </div>
      </>
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
    <>

      {renderContent()}

      {showAvatarModal && (
        <AvatarModal
          currentAvatar={user?.profile?.avatar}
          onClose={() => setShowAvatarModal(false)}
        />
      )}

    </>
  )
}
