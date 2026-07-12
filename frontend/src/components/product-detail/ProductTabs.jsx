// src/components/product-detail/ProductTabs.jsx
import { useState } from "react";
import { MessageSquare, Wrench } from "lucide-react";

/**
 * ProductTabs
 *
 * Tabs:
 *   DESCRIPTION    → product.description
 *   SPECIFICATIONS → built from existing backend fields
 *                    material + weight marked "Not Provided"
 *                    until backend Product model adds those fields
 *   REVIEWS        → placeholder until reviews app ships
 *   COMPATIBILITY  → compatible_bikes[] with year range
 */
export default function ProductTabs({ product }) {
  const [active, setActive] = useState("description");

  const compatible_bikes = product?.compatible_bikes ?? [];

  const tabs = [
    { id: "description",    label: "DESCRIPTION"    },
    { id: "specifications", label: "SPECIFICATIONS" },
    { id: "reviews",        label: "REVIEWS (0)"    },
    { id: "compatibility",  label: "COMPATIBILITY"  },
  ];

  // ── Specifications rows ────────────────────────────────────────────────────
  // Rows built from backend fields we already have.
  // material + weight → "Not Provided" until backend adds those fields.
  // When backend adds them, replace null with product?.material etc.
  const specRows = [
    {
      label: "Part Number",
      value: product?.sku ?? null,
    },
    {
      label: "Category",
      value: product?.category?.name ?? null,
    },
    {
      label: "Brand",
      value: product?.brand?.name ?? "Universal",
    },
    {
      label: "Material",
      // TODO: replace null with product?.material
      // when Product model adds material = CharField(blank=True)
      value: null,
      notProvided: true,
    },
    {
      label: "Weight",
      // TODO: replace null with product?.weight
      // when Product model adds weight = DecimalField(null=True, blank=True)
      value: null,
      notProvided: true,
    },
    {
      label: "Status",
      value: product?.is_in_stock ? "In Stock" : "Out of Stock",
      highlight: product?.is_in_stock,
    },
  ];

  return (
    <div className="mt-4">

      {/* Tab Headers */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`px-5 py-3 text-sm font-bold transition
                        relative whitespace-nowrap shrink-0
                        ${active === tab.id
                          ? "text-primary"
                          : "text-gray-500 hover:text-gray-700"
                        }`}
          >
            {tab.label}
            {active === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5
                               bg-primary rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="py-5">

        {/* ── Description ─────────────────────────────────────────────────── */}
        {active === "description" && (
          <div>
            {product?.description ? (
              <p className="text-sm text-gray-600 leading-relaxed
                            whitespace-pre-line">
                {product.description}
              </p>
            ) : (
              <p className="text-sm text-gray-400 italic">
                No description available.
              </p>
            )}
          </div>
        )}

        {/* ── Specifications ───────────────────────────────────────────────── */}
        {active === "specifications" && (
          <div className="max-w-lg">
            <table className="w-full text-sm">
              <tbody>
                {specRows.map((row, i) => (
                  <tr
                    key={row.label}
                    className={i % 2 === 0 ? "bg-gray-50" : "bg-white"}
                  >
                    {/* Label */}
                    <td className="py-3 px-4 font-semibold text-gray-700 w-36
                                   border-b border-gray-100">
                      {row.label}
                    </td>

                    {/* Value */}
                    <td className="py-3 px-4 border-b border-gray-100">
                      {row.notProvided ? (
                        <span className="inline-flex items-center gap-1.5
                                         text-xs text-gray-400 bg-gray-100
                                         px-2.5 py-1 rounded-md font-medium">
                          <span className="w-1.5 h-1.5 rounded-full
                                           bg-gray-300 shrink-0" />
                          Not Provided
                        </span>
                      ) : row.highlight ? (
                        <span className="text-green-600 font-semibold">
                          {row.value}
                        </span>
                      ) : (
                        <span className="text-gray-600">
                          {row.value ?? "—"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Future fields note */}
            <p className="text-xs text-gray-400 mt-4 italic">
              * Additional specifications will be available soon.
            </p>
          </div>
        )}

        {/* ── Reviews ─────────────────────────────────────────────────────── */}
        {active === "reviews" && (
          <div className="flex flex-col items-center py-8 text-center">
            <MessageSquare
              size={36}
              className="text-gray-300 mb-3"
              strokeWidth={1.5}
            />
            <p className="text-sm font-bold text-gray-700">
              No reviews yet
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Be the first to review this product
            </p>
          </div>
        )}

        {/* ── Compatibility ────────────────────────────────────────────────── */}
        {active === "compatibility" && (
          <div>
            {compatible_bikes.length > 0 ? (
              <>
                <p className="text-sm text-gray-500 mb-3">
                  This part is compatible with the following bike models:
                </p>
                <div className="flex gap-2 flex-wrap">
                  {compatible_bikes.map((bike) => (
                    <span
                      key={bike.id}
                      className="border border-gray-300 px-4 py-1.5
                                 rounded-md text-sm text-gray-700 bg-gray-50"
                    >
                      {bike.display_name}
                      {bike.year_end
                        ? ` (${bike.year_start}–${bike.year_end})`
                        : ` (${bike.year_start}–present)`
                      }
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2 text-green-700
                              bg-green-50 border border-green-200
                              rounded-lg px-4 py-3">
                <Wrench size={16} className="shrink-0" />
                <span className="text-sm font-semibold">
                  Universal — Compatible with all bikes
                </span>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
// // components/product-detail/ProductTabs.jsx
// import { useState } from "react";
// import { CheckCircle2 } from "lucide-react";

// export default function ProductTabs({ product }) {
//   const [active, setActive] = useState("description");

//   const tabs = [
//     { id: "description", label: "DESCRIPTION" },
//     { id: "specifications", label: "SPECIFICATIONS" },
//     { id: "reviews", label: `REVIEWS (${product.reviews})` },
//     { id: "compatibility", label: "COMPATIBILITY" },
//   ];

//   return (
//     <div className="mt-10">

//       {/* Tab Headers */}
//       <div className="flex border-b border-gray-200">
//         {tabs.map((tab) => (
//           <button
//             key={tab.id}
//             onClick={() => setActive(tab.id)}
//             className={`px-6 py-3 text-sm font-bold transition relative
//               ${active === tab.id
//                 ? "text-primary"
//                 : "text-gray-500 hover:text-gray-700"
//               }`}
//           >
//             {tab.label}
//             {active === tab.id && (
//               <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary rounded-full" />
//             )}
//           </button>
//         ))}
//       </div>

//       {/* Tab Content */}
//       <div className="py-6">

//         {active === "description" && (
//           <div>
//             <p className="text-sm text-gray-600 leading-relaxed mb-4">
//               {product.description}
//             </p>
//             <ul className="space-y-2">
//               {product.features.map((f) => (
//                 <li key={f} className="flex items-center gap-2 text-sm text-gray-600">
//                   <CheckCircle2 size={16} className="text-primary shrink-0" />
//                   {f}
//                 </li>
//               ))}
//             </ul>
//           </div>
//         )}

//         {active === "specifications" && (
//           <div className="max-w-lg">
//             <table className="w-full text-sm">
//               <tbody>
//                 {product.specifications.map((spec, i) => (
//                   <tr key={spec.label} className={i % 2 === 0 ? "bg-gray-50" : "bg-white"}>
//                     <td className="py-3 px-4 font-semibold text-gray-700 w-40">{spec.label}</td>
//                     <td className="py-3 px-4 text-gray-600">{spec.value}</td>
//                   </tr>
//                 ))}
//               </tbody>
//             </table>
//           </div>
//         )}

//         {active === "reviews" && (
//           <p className="text-sm text-gray-500">No reviews yet.</p>
//         )}

//         {active === "compatibility" && (
//           <div className="flex gap-2 flex-wrap">
//             {product.compatibility.map((item) => (
//               <span
//                 key={item}
//                 className="border border-gray-300 px-4 py-1.5 rounded-md text-sm text-gray-700"
//               >
//                 {item}
//               </span>
//             ))}
//           </div>
//         )}

//       </div>
//     </div>
//   );
// }