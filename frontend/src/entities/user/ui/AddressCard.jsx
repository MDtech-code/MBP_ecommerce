// src/entities/ui/AddressCard.jsx

import {  Edit3, Trash2, Star } from "lucide-react"

export default function AddressCard({ address, onEdit, onDelete, onSetDefault }) {
  return (
    <div className={`
      relative bg-white rounded-2xl border shadow-sm p-5
      ${address.is_default
        ? "border-primary ring-1 ring-primary/20"
        : "border-gray-100"
      }
    `}>

      {/* Default badge */}
      {address.is_default && (
        <span className="absolute top-4 right-4 bg-primary/10 text-primary text-xs font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
          <Star size={10} fill="currentColor" />
          Default
        </span>
      )}

      {/* Label */}
      <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">
        {address.label_display}
      </p>

      {/* Address lines */}
      <p className="text-sm font-semibold text-gray-800">
        {address.address_line1}
      </p>
      {address.address_line2 && (
        <p className="text-sm text-gray-500">{address.address_line2}</p>
      )}
      {/*phone number */}
        {address.phone && ( <p className="text-sm text-gray-500">{address.phone}</p>)}
      <p className="text-sm text-gray-600 mt-1">
        {address.city}, {address.province_display}
      </p>
      <p className="text-sm text-gray-600">
        {address.postal_code} — {address.country}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-gray-50">

        {!address.is_default && (
          <button
            onClick={() => onSetDefault(address.id)}
            className="text-xs font-bold text-gray-500 hover:text-primary transition-colors flex items-center gap-1"
          >
            <Star size={12} />
            Set Default
          </button>
        )}

        <div className="flex items-center gap-2 ml-auto">
          <button
            onClick={() => onEdit(address)}
            className="flex items-center gap-1 text-xs font-bold text-gray-500 hover:text-primary border border-gray-200 px-3 py-1.5 rounded-lg hover:border-primary transition-colors"
          >
            <Edit3 size={12} />
            Edit
          </button>

          <button
            onClick={() => onDelete(address.id)}
            className="flex items-center gap-1 text-xs font-bold text-red-400 hover:text-red-600 border border-red-100 px-3 py-1.5 rounded-lg hover:border-red-300 transition-colors"
          >
            <Trash2 size={12} />
            Delete
          </button>
        </div>

      </div>
    </div>
  )
}