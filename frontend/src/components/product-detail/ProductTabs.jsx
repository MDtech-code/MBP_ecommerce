// components/product-detail/ProductTabs.jsx
import { useState } from "react";
import { CheckCircle2 } from "lucide-react";

export default function ProductTabs({ product }) {
  const [active, setActive] = useState("description");

  const tabs = [
    { id: "description", label: "DESCRIPTION" },
    { id: "specifications", label: "SPECIFICATIONS" },
    { id: "reviews", label: `REVIEWS (${product.reviews})` },
    { id: "compatibility", label: "COMPATIBILITY" },
  ];

  return (
    <div className="mt-10">

      {/* Tab Headers */}
      <div className="flex border-b border-gray-200">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`px-6 py-3 text-sm font-bold transition relative
              ${active === tab.id
                ? "text-primary"
                : "text-gray-500 hover:text-gray-700"
              }`}
          >
            {tab.label}
            {active === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="py-6">

        {active === "description" && (
          <div>
            <p className="text-sm text-gray-600 leading-relaxed mb-4">
              {product.description}
            </p>
            <ul className="space-y-2">
              {product.features.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
                  <CheckCircle2 size={16} className="text-primary shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
        )}

        {active === "specifications" && (
          <div className="max-w-lg">
            <table className="w-full text-sm">
              <tbody>
                {product.specifications.map((spec, i) => (
                  <tr key={spec.label} className={i % 2 === 0 ? "bg-gray-50" : "bg-white"}>
                    <td className="py-3 px-4 font-semibold text-gray-700 w-40">{spec.label}</td>
                    <td className="py-3 px-4 text-gray-600">{spec.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {active === "reviews" && (
          <p className="text-sm text-gray-500">No reviews yet.</p>
        )}

        {active === "compatibility" && (
          <div className="flex gap-2 flex-wrap">
            {product.compatibility.map((item) => (
              <span
                key={item}
                className="border border-gray-300 px-4 py-1.5 rounded-md text-sm text-gray-700"
              >
                {item}
              </span>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}