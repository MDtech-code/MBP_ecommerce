// src/components/account/security/PasswordStrength.jsx

import RequirementItem from "./RequirementItem";

/**
 * Evaluates password strength in real time.
 * Receives the raw password string as a prop.
 * Drives both the requirement checklist and the strength bar.
 * No state needed — pure derivation from the password prop.
 */

const REQUIREMENTS = [
  {
    key: "minLength",
    label: "Minimum 8 characters",
    test: (p) => p.length >= 8,
  },
  {
    key: "uppercase",
    label: "One uppercase letter",
    test: (p) => /[A-Z]/.test(p),
  },
  {
    key: "lowercase",
    label: "One lowercase letter",
    test: (p) => /[a-z]/.test(p),
  },
  {
    key: "number",
    label: "One number",
    test: (p) => /[0-9]/.test(p),
  },
  {
    key: "special",
    label: "One special character",
    test: (p) => /[^A-Za-z0-9]/.test(p),
  },
];

/**
 * Maps number of satisfied requirements to a strength level.
 * 0-1 → Weak
 * 2-3 → Fair
 * 4   → Good
 * 5   → Strong
 */
function getStrength(satisfiedCount) {
  if (satisfiedCount <= 1) {
    return {
      label: "Weak",
      width: "w-1/5",
      color: "bg-red-500",
      textColor: "text-red-500",
    };
  }

  if (satisfiedCount <= 3) {
    return {
      label: "Fair",
      width: "w-2/5",
      color: "bg-yellow-400",
      textColor: "text-yellow-500",
    };
  }

  if (satisfiedCount === 4) {
    return {
      label: "Good",
      width: "w-3/5",
      color: "bg-blue-500",
      textColor: "text-blue-500",
    };
  }

  return {
    label: "Strong",
    width: "w-full",
    color: "bg-green-500",
    textColor: "text-green-600",
  };
}

export default function PasswordStrength({ password = "" }) {
  const results = REQUIREMENTS.map((req) => ({
    ...req,
    satisfied: password.length > 0 && req.test(password),
  }));

  const satisfiedCount = results.filter((r) => r.satisfied).length;

  // When field is empty show neutral state — no strength label, empty bar
  const isEmpty = password.length === 0;
  const strength = isEmpty ? null : getStrength(satisfiedCount);

  return (
    <div className="space-y-5">

      <div>
        <div className="flex justify-between mb-2">
          <span className="text-sm font-semibold">
            Password Strength
          </span>

          {strength && (
            <span className={`text-sm font-bold ${strength.textColor}`}>
              {strength.label}
            </span>
          )}
        </div>

        <div className="h-2 rounded-full bg-gray-200 overflow-hidden">
          {strength && (
            <div
              className={`
                h-full
                rounded-full
                transition-all
                duration-300
                ${strength.width}
                ${strength.color}
              `}
            />
          )}
        </div>
      </div>

      <div className="grid gap-3">
        {results.map((req) => (
          <RequirementItem key={req.key} satisfied={req.satisfied}>
            {req.label}
          </RequirementItem>
        ))}
      </div>

    </div>
  );
}
