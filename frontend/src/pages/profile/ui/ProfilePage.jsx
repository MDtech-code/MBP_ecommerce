// src/pages/profile/ProfilePage.jsx


import { useState } from "react"
import { useNavigate } from "react-router-dom"

import { ProfileView }    from "@entities/user"
import { ProfileEditForm } from "@features/profile"
import { AvatarModal }    from "@features/profile"
import { useProfile }     from "@features/profile"
import { hasAuthToken }   from "@shared/lib"
import { useAuthStore }   from "@entities/user"

export default function ProfilePage() {
  const navigate = useNavigate()
  const user     = useAuthStore((state) => state.user)

  const [mode, setMode]                 = useState("view")
  const [showAvatarModal, setShowAvatarModal] = useState(false)

  const { isLoading } = useProfile({
    enabled: hasAuthToken() || !user,
  })

  if (isLoading && !user) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="loading loading-spinner loading-md text-primary" />
      </div>
    )
  }

  return (
    <div>
      {mode === "edit" ? (
        <ProfileEditForm onCancel={() => setMode("view")} />
      ) : (
        <ProfileView
          user={user}
          onEdit={() => setMode("edit")}
          onAvatarClick={() => setShowAvatarModal(true)}
          onManageAddresses={() => navigate("/addresses")}
        />
      )}

      {showAvatarModal && (
        <AvatarModal
          currentAvatar={user?.profile?.avatar}
          onClose={() => setShowAvatarModal(false)}
        />
      )}
    </div>
  )
}
