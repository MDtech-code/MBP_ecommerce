// widgets/auth/ui/AuthPageHeader.jsx

export function AuthPageHeader({ title, subtitle }) {
  return (
    <div className="hidden lg:block">
      <h2 className="text-3xl font-black text-gray-900 dark:text-gray-100">
        {title}
      </h2>

      {subtitle && (
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          {subtitle}
        </p>
      )}
    </div>
  );
}