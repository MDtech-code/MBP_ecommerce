// src/entities/ui/ProfileInfoRow.jsx

export default function ProfileInfoRow({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-50 dark:border-gray-800/60 last:border-0">
      {/* ── OLD ──────────────────────────────────────────────────────
      <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center shrink-0 mt-0.5">
        <Icon size={15} className="text-primary" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
          {label}
        </p>
        <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate">
          {value || (
            <span className="text-gray-300 font-normal">Not provided</span>
          )}
        </p>
      </div>
      ─────────────────────────────────────────────────────────────── */}

      {/* ── NEW — dark mode added throughout ─────────────────────── */}
      <div className="w-8 h-8 rounded-lg bg-red-50 dark:bg-red-900/20 flex items-center justify-center shrink-0 mt-0.5">
        <Icon size={15} className="text-primary" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wide">
          {label}
        </p>
        <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 mt-0.5 truncate">
          {value || (
            <span className="text-gray-300 dark:text-gray-600 font-normal">
              Not provided
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
// // src/entities/ui/ProfileInfoRow.jsx

// export default function ProfileInfoRow({ icon: Icon, label, value }) {
//   return (
//     <div className="flex items-start gap-3 py-3 border-b border-gray-50 last:border-0">
//       <div className="w-8 h-8 rounded-lg bg-red-50 flex items-center justify-center shrink-0 mt-0.5">
//         <Icon size={15} className="text-primary" />
//       </div>
//       <div className="min-w-0">
//         <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
//           {label}
//         </p>
//         <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate">
//           {value || (
//             <span className="text-gray-300 font-normal">Not provided</span>
//           )}
//         </p>
//       </div>
//     </div>
//   )
// }