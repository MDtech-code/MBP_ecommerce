// shared/ui/AuthIconBadge.jsx
//
// Reusable icon circle used on all auth info/status pages.
// Renders a centered icon inside a circular gray container.
// Optionally renders a small primary-colored badge in the bottom-right corner.
//
// Props:
//   icon   — Lucide icon component (required)
//   badge  — string character to show in badge (optional)
//             pass null or omit for no badge (ForgotPasswordSent)
//
// Usage:
//   <AuthIconBadge icon={MailCheck} badge="✓" />
//   <AuthIconBadge icon={Mail} />              ← no badge

export default function AuthIconBadge({ icon: Icon, badge = null }) {
  return (
    <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
      <Icon size={45} className="text-gray-700" />

      {badge !== null && (
        <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
          {badge} 
        </span>
      )}
    </div>
  );
}