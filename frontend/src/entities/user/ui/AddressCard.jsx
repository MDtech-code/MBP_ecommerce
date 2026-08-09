// src/entities/ui/AddressCard.jsx
//
// Changes:
//   - Full dark mode added
//   - window.confirm removed — replaced with inline confirmation state
//     Delete button shows "Are you sure?" + Confirm/Cancel inline on card
//     No blocking dialog, fully branded, works in all browser contexts

import { useState } from "react"
import { Edit3, Trash2, Star } from "lucide-react"

export default function AddressCard({
  address,
  onEdit,
  onDelete,
  onSetDefault,
  isDeleting,
  isSettingDefault,
}) {
  // ── OLD ────────────────────────────────────────────────────────────
  // No confirmation state — used window.confirm which is blocking,
  // unbranded, and suppressed in some embedded browser contexts.
  // ───────────────────────────────────────────────────────────────────

  // ── NEW — inline confirmation state ────────────────────────────────
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleDeleteClick = () => setConfirmDelete(true)
  const handleDeleteCancel = () => setConfirmDelete(false)
  const handleDeleteConfirm = () => {
    setConfirmDelete(false)
    onDelete(address.id)
  }
  // ───────────────────────────────────────────────────────────────────

  return (
    <div
      className={`
        relative rounded-2xl border shadow-sm p-5 transition-colors
        bg-white dark:bg-[#0a0a0a]
        ${address.is_default
          ? "border-primary ring-1 ring-primary/20"
          : "border-gray-100 dark:border-gray-800"
        }
      `}
    >
      {/* Default badge */}
      {address.is_default && (
        <span className="absolute top-4 right-4 bg-primary/10 text-primary text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
          <Star size={10} fill="currentColor" />
          Default
        </span>
      )}

      {/* Label */}
      <p className="text-xs font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wide mb-2">
        {address.label_display}
      </p>

      {/* Address lines */}
      <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">
        {address.address_line1}
      </p>
      {address.address_line2 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {address.address_line2}
        </p>
      )}
      {address.phone && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {address.phone}
        </p>
      )}
      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
        {address.city}, {address.province_display}
      </p>
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {address.postal_code} — {address.country}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-50 dark:border-gray-800/60">

        {!address.is_default && !confirmDelete && (
          <button
            onClick={() => onSetDefault(address.id)}
            disabled={isSettingDefault}
            className="text-xs font-bold text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-primary transition-colors flex items-center gap-1 disabled:opacity-50"
          >
            <Star size={12} />
            Set Default
          </button>
        )}

        {/* ── OLD ────────────────────────────────────────────────────
        <div className="flex items-center gap-2 ml-auto">
          <button onClick={() => onEdit(address)} ...>Edit</button>
          <button onClick={() => onDelete(address.id)} ...>Delete</button>
        </div>
        ─────────────────────────────────────────────────────────────── */}

        {/* ── NEW — inline delete confirmation ─────────────────────── */}
        {confirmDelete ? (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Delete this address?
            </span>
            <button
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="text-xs font-bold text-white bg-red-500 hover:bg-red-600 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
            >
              {isDeleting ? "Deleting..." : "Yes, Delete"}
            </button>
            <button
              onClick={handleDeleteCancel}
              className="text-xs font-bold text-gray-500 dark:text-gray-400 border border-gray-200 dark:border-gray-700 px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              Cancel
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 ml-auto">
            <button
              onClick={() => onEdit(address)}
              className="flex items-center gap-1 text-xs font-bold text-gray-500 dark:text-gray-400 hover:text-primary dark:hover:text-primary border border-gray-200 dark:border-gray-700 px-3 py-1.5 rounded-lg hover:border-primary dark:hover:border-primary transition-colors"
            >
              <Edit3 size={12} />
              Edit
            </button>
            <button
              onClick={handleDeleteClick}
              className="flex items-center gap-1 text-xs font-bold text-red-400 hover:text-red-600 border border-red-100 dark:border-red-900/40 px-3 py-1.5 rounded-lg hover:border-red-300 dark:hover:border-red-700 transition-colors"
            >
              <Trash2 size={12} />
              Delete
            </button>
          </div>
        )}
        {/* ─────────────────────────────────────────────────────────── */}

      </div>
    </div>
  )
}