// src/components/products/ProductToolbar.jsx

/**
 * ProductToolbar — showing_from, showing_to, total from backend meta.
 *
 * Props:
 *   meta       : pagination meta from useProductList
 *   activeSort : current sort key string
 *   onSort     : (sortKey: string) => void
 */

const SORT_OPTIONS = [
  { value: "newest",     label: "Newest First"      },
  { value: "featured",   label: "Featured"          },
  { value: "price_asc",  label: "Price Low to High" },
  { value: "price_desc", label: "Price High to Low" },
  { value: "name_asc",   label: "Name A–Z"          },
];

export default function ProductToolbar({ meta = {}, activeSort = "newest", onSort }) {
  const { showing_from = 0, showing_to = 0, total = 0 } = meta;

  return (
    <div className="flex justify-between items-center mb-6">

      {/* Result count */}
      <p className="text-sm text-gray-600">
        {total > 0 ? (
          <>
            Showing{" "}
            <span className="font-semibold">{showing_from}–{showing_to}</span>
            {" "}of{" "}
            <span className="font-semibold">{total} products</span>
          </>
        ) : (
          <span className="font-semibold">No products found</span>
        )}
      </p>

      {/* Sort */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600 font-medium">Sort By:</span>
        <select
          value={activeSort}
          onChange={(e) => onSort?.(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2
                     text-sm outline-none bg-white cursor-pointer
                     hover:border-primary transition"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

    </div>
  );
}
// // ProductToolbar.jsx
// export default function ProductToolbar() {
//   return (
//     <div className="flex justify-between items-center mb-6">
      
//       <p className="text-sm text-gray-600">
//         Showing 1–12 of <span className="font-semibold">540 products</span>
//       </p>

//       <div className="flex items-center gap-2">
//         <span className="text-sm text-gray-600 font-medium">Sort By:</span>
//         <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none bg-white cursor-pointer">
//           <option>Featured</option>
//           <option>Price Low to High</option>
//           <option>Price High to Low</option>
//           <option>Newest First</option>
//         </select>
//       </div>

//     </div>
//   );
// }
// export default function ProductToolbar(){


// return (

// <div
// className="
// flex
// justify-between
// items-center
// mb-8
// "
// >


// <p
// className="
// font-semibold
// "
// >

// Showing 1-12 Products

// </p>



// <select

// className="
// border
// rounded-lg
// px-4
// py-2
// outline-none
// "

// >

// <option>
// Sort by Featured
// </option>


// <option>
// Price Low to High
// </option>


// <option>
// Price High to Low
// </option>


// </select>



// </div>

// )

// }