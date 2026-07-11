// src/components/profile/AvatarModal.jsx
import { useRef, useState } from "react"
import { X, Camera, Upload, UserRound } from "lucide-react"
import Portal from "../../common/Portal"
import { useUploadAvatar } from "../../../hooks/account/useAuthMutations"
import { getMediaUrl } from "../../../utils/media"
import { normalizeError } from "../../../api/transformers"

export default function AvatarModal({ currentAvatar, onClose }) {
  const fileRef = useRef(null)
  const [preview, setPreview] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)

  const {
    mutate: uploadAvatar,
    isPending,
    isError,
    error,
  } = useUploadAvatar()

  const normalized = isError ? normalizeError(error) : null
  const uploadError =
  normalized?.errors?.fields?.avatar?.message ??
  normalized?.errors?.non_fields?.message ??
  normalized?.message ??
  null

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setSelectedFile(file)
    setPreview(URL.createObjectURL(file))
  }

  const handleUpload = () => {
    if (!selectedFile) return
    const formData = new FormData()
    formData.append("avatar", selectedFile)
    uploadAvatar(formData, {
      onSuccess: () => onClose(),
    })
  }

  return (
    <Portal>
      {/* Full screen overlay — fixed, covers everything */}
      <div className="fixed inset-0 z-50 flex items-center justify-center">

        {/* Backdrop — blurred, click to close */}
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />

        {/* Modal box — above backdrop */}
        <div className="relative z-10 bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">

          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h3 className="font-black text-gray-900 text-lg">Update Photo</h3>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors"
            >
              <X size={18} className="text-gray-500" />
            </button>
          </div>

          {/* Preview */}
          <div className="px-6 py-6 flex flex-col items-center gap-4">

            <div className="w-32 h-32 rounded-full bg-gray-100 overflow-hidden border-4 border-gray-200 flex items-center justify-center">
              {preview ? (
                <img
                  src={preview}
                  alt="Preview"
                  className="w-full h-full object-cover"
                />
              ) : currentAvatar ? (
                <img
                  src={getMediaUrl(currentAvatar)}
                  alt="Current avatar"
                  className="w-full h-full object-cover"
                />
              ) : (
                <UserRound size={60} className="text-gray-300" />
              )}
            </div>

            {uploadError && (
              <div
                role="alert"
                className="w-full text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-center"
              >
                {uploadError}
              </div>
            )}

            {/* Hidden file input */}
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleFileSelect}
            />

            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-2 border border-gray-200 text-gray-700 px-5 py-2.5 rounded-lg text-sm font-semibold hover:border-primary hover:text-primary transition-colors"
            >
              <Camera size={16} />
              {preview ? "Choose Different" : "Choose Photo"}
            </button>

            <p className="text-xs text-gray-400 text-center">
              JPEG, PNG or WebP · Max 2MB
            </p>

          </div>

          {/* Footer */}
          <div className="flex gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-lg text-sm font-bold hover:bg-gray-100 transition-colors"
            >
              CANCEL
            </button>
            <button
              type="button"
              onClick={handleUpload}
              disabled={!selectedFile || isPending}
              className="flex-1 bg-primary text-white py-2.5 rounded-lg text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isPending ? (
                <span className="text-sm">UPLOADING...</span>
              ) : (
                <>
                  <Upload size={15} />
                  UPLOAD
                </>
              )}
            </button>
          </div>

        </div>
      </div>
    </Portal>
  )
}