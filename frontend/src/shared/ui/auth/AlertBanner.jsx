
  const variantMap = {
    error: {
      role: "alert",
      className:
        "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
    },
    success: {
      role: "status",
      className:
        "text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
    },
    info: {
      role: "status",
      className:
        "text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
    },
  };

  export default function AlertBanner({ type = "error", children, className = "" }) {
    const variant = variantMap[type];

    return (
      <div
        role={variant.role}
        className={`text-sm border rounded-lg px-4 py-3 ${variant.className} ${className}`}
      >
        {children} 
      </div>
    );
  }