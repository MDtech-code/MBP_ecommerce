// src/pages/security/ui/DeleteAccountPage.jsx

import { Trash2,  ArrowLeft, AlertTriangle, X } from "lucide-react";
import { Link }      from "react-router-dom";
import { useDeleteAccountForm } from "@features/auth";

export default function DeleteAccountPage() {
  const {
    showConfirm,
    formError,
    isPending,
    handleDeleteClick,
    handleCancel,
    handleConfirmedDelete,
  } = useDeleteAccountForm();

  return (
    <>
      <div className="w-full">

        {/* Back */}
        <Link
          to="/security"
          className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-primary transition-colors mb-8"
        >
          <ArrowLeft size={18} />
          Back to Security
        </Link>

        {/* Card */}
        <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8 lg:p-10">

          {/* Header */}
          <div className="flex items-center gap-4 mb-3">
            <div className="p-3 bg-red-50 rounded-2xl">
              <Trash2 size={24} className="text-red-500" />
            </div>
            <h1 className="text-3xl font-black text-gray-900">
              Delete Account
            </h1>
          </div>

          <p className="text-gray-500 max-w-xl">
            Permanently delete your BikeExpress account.
            This action <span className="font-semibold text-red-500">cannot be undone</span> —
            all your data will be removed immediately.
          </p>

          {/* What gets deleted */}
          <div className="mt-8 max-w-xl">
            <p className="text-sm font-semibold text-gray-700 mb-3">
              What will be permanently deleted:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                "Profile & personal information",
                "All order history",
                "Saved addresses",
                "Cart & wishlist items",
                "Account preferences",
                "Social login connections",
              ].map((item) => (
                <div
                  key={item}
                  className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-xl px-4 py-2.5"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0" />
                  {item}
                </div>
              ))}
            </div>
          </div>

          {/* Danger action */}
          <div className="mt-10 max-w-xl">
            <div className="flex items-start gap-3 bg-red-50 border border-red-100 rounded-xl px-4 py-3 mb-6">
              <AlertTriangle size={18} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700">
                Once deleted, your account cannot be recovered.
                Please make sure you have saved anything you need.
              </p>
            </div>

            <button
              type="button"
              onClick={handleDeleteClick}
              className="w-full sm:w-auto rounded-xl bg-red-500 hover:bg-red-600 px-8 py-3.5 font-bold text-white transition-all"
            >
              DELETE MY ACCOUNT
            </button>
          </div>

        </div>
      </div>

      {/* ── Confirm Modal ────────────────────────────────────────────────────── */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4">

          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={handleCancel}
          />

          {/* Modal */}
          <div className="relative bg-white rounded-3xl shadow-2xl p-8 w-full max-w-md z-10">

            {/* Close */}
            <button
              type="button"
              onClick={handleCancel}
              className="absolute top-5 right-5 text-gray-400 hover:text-gray-600 transition"
            >
              <X size={20} />
            </button>

            {/* Icon + Title */}
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2.5 bg-red-50 rounded-xl">
                <AlertTriangle size={22} className="text-red-500" />
              </div>
              <h3 className="text-xl font-black text-gray-900">
                Confirm Deletion
              </h3>
            </div>

            <p className="text-sm text-gray-500 mb-6 mt-1">
              Are you sure? 
              This is permanent and cannot be undone.
            </p>

            {/* Form error */}
            {formError && (
              <div
                role="alert"
                className="mb-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3"
              >
                {formError}
              </div>
            )}

            <form onSubmit={handleConfirmedDelete} className="space-y-5">

              

              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={handleCancel}
                  className="flex-1 border border-gray-200 text-gray-700 py-3 rounded-xl font-semibold hover:bg-gray-50 transition text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isPending}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white py-3 rounded-xl font-bold transition disabled:opacity-60 disabled:cursor-not-allowed text-sm"
                >
                  {isPending ? "DELETING..." : "YES, DELETE"}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}
    </>
  );
}