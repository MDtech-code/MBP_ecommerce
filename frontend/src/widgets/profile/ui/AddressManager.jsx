// src/widgets/profile/AddressManager.jsx


import { useState } from "react"
import { Plus } from "lucide-react"
import { AddressCard } from "@entities/user"
import { AddressForm } from "@features/address"
import { useDeleteAddress, useSetDefaultAddress } from "@features/address"
import { useAuthStore } from "@entities/user"

export default function AddressManager() {
  const user      = useAuthStore((state) => state.user)
  const addresses = user?.addresses ?? []

  const [mode, setMode]          = useState("list")
  const [editingAddress, setEditing] = useState(null)

  const { mutate: deleteAddress,     isPending: isDeleting      } = useDeleteAddress()
  const { mutate: setDefaultAddress, isPending: isSettingDefault } = useSetDefaultAddress()

  const handleEdit = (address) => {
    setEditing(address)
    setMode("edit")
  }

  const handleDelete = (id) => {
    deleteAddress(id)
  }

  const handleSetDefault = (id) => {
    setDefaultAddress(id)
  }

  const handleFormDone = () => {
    setMode("list")
    setEditing(null)
  }

  if (mode === "add" || mode === "edit") {
    return (
      <AddressForm
        existingAddress={mode === "edit" ? editingAddress : null}
        onCancel={handleFormDone}
      />
    )
  }

  return (
    <div className="space-y-6">

      
      <div className="bg-white dark:bg-[#0a0a0a] rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black text-gray-900 dark:text-gray-100">
              My Addresses
            </h2>
            <p className="text-gray-400 dark:text-gray-500 text-sm mt-0.5">
              {addresses.length === 0
                ? "No addresses saved yet"
                : `${addresses.length} address${addresses.length !== 1 ? "es" : ""} saved`
              }
            </p>
          </div>
          <button
            onClick={() => setMode("add")}
            className="flex items-center gap-2 bg-primary text-white px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:opacity-90 transition-opacity touch-manipulation"
          >
            <Plus size={14} />
            ADD ADDRESS
          </button>
        </div>
      </div>

      {/* Empty state */}
      {addresses.length === 0 && (
        <div className="bg-white dark:bg-[#0a0a0a] rounded-2xl border border-dashed border-gray-200 dark:border-gray-700 p-12 text-center">
          <div className="w-12 h-12 rounded-2xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center mx-auto mb-3">
            <Plus size={24} className="text-gray-300 dark:text-gray-600" />
          </div>
          <p className="text-sm font-semibold text-gray-400 dark:text-gray-500">
            No addresses saved yet
          </p>
          <p className="text-xs text-gray-300 dark:text-gray-600 mt-1">
            Add an address to speed up checkout
          </p>
          <button
            onClick={() => setMode("add")}
            className="mt-4 text-xs font-bold text-primary hover:underline"
          >
            Add your first address
          </button>
        </div>
      )}

      {/* Address cards grid */}
      {addresses.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {addresses.map((address) => (
            <AddressCard
              key={address.id}
              address={address}
              onEdit={handleEdit}
              onDelete={handleDelete}
              onSetDefault={handleSetDefault}
              isDeleting={isDeleting}
              isSettingDefault={isSettingDefault}
            />
          ))}
        </div>
      )}

    </div>
  )
}
