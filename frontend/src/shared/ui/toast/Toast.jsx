// shared/ui/Toast.jsx

import { useEffect, useRef, useState } from "react";
import {
  
  CircleAlert,
  CircleCheck,
  Info,
} from "lucide-react";

const DURATION = 3000;

const variantMap = {
  error: {
    role: "alert",
    icon: CircleAlert,
    container:
      "border-red-200 bg-red-50 text-red-700 dark:border-red-800 dark:bg-neutral-900 dark:text-red-400",
    progress: "bg-red-500",
  },

  success: {
    role: "status",
    icon: CircleCheck,
    container:
      "border-green-200 bg-green-50 text-green-700 dark:border-green-800 dark:bg-neutral-900 dark:text-green-400",
    progress: "bg-green-500",
  },

  info: {
    role: "status",
    icon: Info,
    container:
      "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-800 dark:bg-neutral-900 dark:text-blue-400",
    progress: "bg-blue-500",
  },
};

export default function Toast({
  type = "error",
  children,
  onClose,
  duration = DURATION,
}) {
  const variant = variantMap[type];
  const Icon = variant.icon;

  const [visible, setVisible] = useState(false);
  const [paused, setPaused] = useState(false);
  const [progress, setProgress] = useState(100);

  const intervalRef = useRef(null);

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true));

    const step = 100 / (duration / 30);

    intervalRef.current = setInterval(() => {
      if (paused) return;

      setProgress((prev) => {
        const next = prev - step;

        if (next <= 0) {
          clearInterval(intervalRef.current);

          setVisible(false);

          setTimeout(() => {
            onClose?.();
          }, 250);

          return 0;
        }

        return next;
      });
    }, 30);

    return () => clearInterval(intervalRef.current);
  }, [paused, duration, onClose]);

  

  return (
    <div
      role={variant.role}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      className={`
        fixed
        bottom-2
        right-6
        z-99999

        w-100
        max-w-[calc(100vw-2rem)]

        overflow-hidden
        rounded-xl
        border

        shadow-2xl
        ring-1
        ring-black/5

        transition-all
        duration-300
        ease-out

        ${
          visible
            ? "translate-x-0 opacity-100"
            : "translate-x-10 opacity-0"
        }

        ${variant.container}
      `}
    >
      <div className="flex items-start gap-3 p-4">

        <Icon
          size={22}
          className="mt-0.5 shrink-0"
        />

        <p className="flex-1 text-sm font-medium leading-6">
          {children}
        </p>

        
      </div>

      <div className="h-1 w-full bg-black/5 dark:bg-white/10">
        <div
          className={`h-full ${variant.progress}`}
          style={{
            width: `${progress}%`,
            transition: paused ? "none" : "width 30ms linear",
          }}
        />
      </div>
    </div>
  );
}