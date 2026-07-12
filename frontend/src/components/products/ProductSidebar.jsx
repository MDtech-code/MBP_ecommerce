// src/components/products/ProductSidebar.jsx
import { ChevronDown } from "lucide-react";
import { useCategoriesFlat } from "../../hooks/products/useProductQueries";
import { useBrands }          from "../../hooks/products/useProductQueries";
import { useBikeModels }      from "../../hooks/products/useProductQueries";

/**
 * ProductSidebar — all data from backend, all filter state from useProductList.
 *
 * Props (all from useProductList hook in parent page):
 *   activeFilters  : { category, brand, bikeModel, minPrice, maxPrice }
 *   setCategory    : (slug: string|null) => void
 *   setBrand       : (slug: string|null) => void
 *   setBikeModel   : (id: string|null) => void
 *   setMinPrice    : (val: string|null) => void
 *   setMaxPrice    : (val: string|null) => void
 *   clearFilters   : () => void
 *
 * Why only root categories in sidebar:
 *   Flat list from backend includes ALL categories (root + sub).
 *   We filter to is_subcategory=false for the sidebar top-level list.
 *   Subcategory drill-down is handled by the mega menu, not sidebar.
 *   Sidebar checkbox selects a category slug → filters products.
 */
export default function ProductSidebar({
  activeFilters = {},
  setCategory,
  setBrand,
  setBikeModel,
  setMinPrice,
  setMaxPrice,
  clearFilters,
}) {
  const { data: allCategories = [], isLoading: catsLoading } = useCategoriesFlat();
  const { data: brands        = [], isLoading: brandsLoading } = useBrands();
  const { data: bikeModels    = [], isLoading: bikesLoading  } = useBikeModels();

  // Only root categories in sidebar
  const rootCategories = allCategories.filter((c) => !c.is_subcategory);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleCategoryToggle = (slug) => {
    // Toggle — clicking active category deselects it
    setCategory(activeFilters.category === slug ? null : slug);
  };

  const handleBrandToggle = (slug) => {
    setBrand(activeFilters.brand === slug ? null : slug);
  };

  const handleBikeChange = (e) => {
    setBikeModel(e.target.value || null);
  };

  const handleMinPrice = (e) => {
    setMinPrice(e.target.value || null);
  };

  const handleMaxPrice = (e) => {
    setMaxPrice(e.target.value || null);
  };

  // ── Active filter count for "Clear" button ───────────────────────────────
  const activeCount = [
    activeFilters.category,
    activeFilters.brand,
    activeFilters.bikeModel,
    activeFilters.minPrice,
    activeFilters.maxPrice,
  ].filter(Boolean).length;

  return (
    <div className="space-y-6">

      {/* Clear filters */}
      {activeCount > 0 && (
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500 font-semibold">
            {activeCount} filter{activeCount > 1 ? "s" : ""} active
          </span>
          <button
            onClick={clearFilters}
            className="text-primary text-xs font-bold hover:underline"
          >
            Clear All
          </button>
        </div>
      )}

      {/* ── Categories ──────────────────────────────────────────────────────── */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Categories
        </h3>

        {catsLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-5 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-2.5">
            {rootCategories.map((cat) => (
              <label
                key={cat.id}
                className="flex items-center justify-between
                           text-sm cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={activeFilters.category === cat.slug}
                    onChange={() => handleCategoryToggle(cat.slug)}
                    className="w-4 h-4 rounded border-gray-300
                               accent-primary cursor-pointer"
                  />
                  <span className="text-gray-700 group-hover:text-primary
                                   transition">
                    {cat.name}
                  </span>
                </div>
                {cat.subcategory_count > 0 && (
                  <span className="text-gray-400 text-xs">
                    ({cat.subcategory_count})
                  </span>
                )}
              </label>
            ))}
          </div>
        )}
      </div>

      <hr className="border-gray-200" />

      {/* ── Brand ───────────────────────────────────────────────────────────── */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Brand
        </h3>

        {brandsLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-5 bg-gray-100 rounded animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-2.5">
            {brands.map((brand) => (
              <label
                key={brand.id}
                className="flex items-center justify-between
                           text-sm cursor-pointer group"
              >
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={activeFilters.brand === brand.slug}
                    onChange={() => handleBrandToggle(brand.slug)}
                    className="w-4 h-4 rounded border-gray-300
                               accent-primary cursor-pointer"
                  />
                  <span className="text-gray-700 group-hover:text-primary
                                   transition">
                    {brand.name}
                  </span>
                </div>
              </label>
            ))}
          </div>
        )}
      </div>

      <hr className="border-gray-200" />

      {/* ── Price Range ─────────────────────────────────────────────────────── */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Price Range
        </h3>

        <div className="flex gap-2">
          <div className="flex-1">
            <input
              type="number"
              placeholder="Min"
              value={activeFilters.minPrice || ""}
              onChange={handleMinPrice}
              className="w-full border border-gray-300 rounded-lg px-3 py-2
                         text-sm outline-none focus:border-primary transition"
            />
          </div>
          <span className="flex items-center text-gray-400 text-sm">—</span>
          <div className="flex-1">
            <input
              type="number"
              placeholder="Max"
              value={activeFilters.maxPrice || ""}
              onChange={handleMaxPrice}
              className="w-full border border-gray-300 rounded-lg px-3 py-2
                         text-sm outline-none focus:border-primary transition"
            />
          </div>
        </div>

        {/* Quick price buttons */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {[
            { label: "Under 500",  min: null,  max: 500   },
            { label: "500–2000",   min: 500,   max: 2000  },
            { label: "2000–5000",  min: 2000,  max: 5000  },
            { label: "5000+",      min: 5000,  max: null  },
          ].map(({ label, min, max }) => (
            <button
              key={label}
              onClick={() => {
                setMinPrice(min?.toString() ?? null);
                setMaxPrice(max?.toString() ?? null);
              }}
              className="text-xs border border-gray-300 rounded-md px-2.5 py-1
                         text-gray-600 hover:border-primary hover:text-primary
                         transition"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <hr className="border-gray-200" />

      {/* ── Bike Model ──────────────────────────────────────────────────────── */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Bike Model
        </h3>

        {bikesLoading ? (
          <div className="h-10 bg-gray-100 rounded animate-pulse" />
        ) : (
          <div className="relative">
            <select
              value={activeFilters.bikeModel || ""}
              onChange={handleBikeChange}
              className="w-full border border-gray-300 rounded-lg px-3 py-2.5
                         text-sm text-gray-600 outline-none appearance-none
                         cursor-pointer bg-white focus:border-primary transition"
            >
              <option value="">All Bike Models</option>
              {bikeModels.map((bike) => (
                <option key={bike.id} value={bike.id}>
                  {bike.display_name}
                </option>
              ))}
            </select>
            <ChevronDown
              size={16}
              className="absolute right-3 top-1/2 -translate-y-1/2
                         text-gray-400 pointer-events-none"
            />
          </div>
        )}
      </div>

    </div>
  );
}
// // ProductSidebar.jsx
// import { ChevronDown } from "lucide-react";

// const categories = [
//   { name: "Engine Parts", count: 120 },
//   { name: "Brake System", count: 85 },
//   { name: "Electricals", count: 60 },
//   { name: "Drive & Transmission", count: 75 },
//   { name: "Body Parts", count: 95 },
//   { name: "Accessories", count: 110 },
// ];

// const brands = [
//   { name: "Honda", count: 45 },
//   { name: "Yamaha", count: 38 },
//   { name: "Suzuki", count: 32 },
//   { name: "Atlas Honda", count: 28 },
//   { name: "Unique", count: 22 },
// ];

// export default function ProductSidebar() {
//   return (
//     <div className="space-y-6">

//       {/* Categories */}
//       <div>
//         <h3 className="font-black text-sm uppercase tracking-wide mb-4">
//           Categories
//         </h3>
//         <div className="space-y-2.5">
//           {categories.map((item) => (
//             <label
//               key={item.name}
//               className="flex items-center justify-between text-sm cursor-pointer group"
//             >
//               <div className="flex items-center gap-2">
//                 <input
//                   type="checkbox"
//                   className="w-4 h-4 rounded border-gray-300 accent-primary cursor-pointer"
//                 />
//                 <span className="text-gray-700 group-hover:text-primary transition">
//                   {item.name}
//                 </span>
//               </div>
//               <span className="text-gray-400 text-xs">({item.count})</span>
//             </label>
//           ))}
//         </div>
//       </div>

//       {/* Divider */}
//       <hr className="border-gray-200" />

//       {/* Brand */}
//       <div>
//         <h3 className="font-black text-sm uppercase tracking-wide mb-4">
//           Brand
//         </h3>
//         <div className="space-y-2.5">
//           {brands.map((item) => (
//             <label
//               key={item.name}
//               className="flex items-center justify-between text-sm cursor-pointer group"
//             >
//               <div className="flex items-center gap-2">
//                 <input
//                   type="checkbox"
//                   className="w-4 h-4 rounded border-gray-300 accent-primary cursor-pointer"
//                 />
//                 <span className="text-gray-700 group-hover:text-primary transition">
//                   {item.name}
//                 </span>
//               </div>
//               <span className="text-gray-400 text-xs">({item.count})</span>
//             </label>
//           ))}
//         </div>
//         <button className="text-primary text-sm font-semibold mt-3 hover:underline">
//           View More +
//         </button>
//       </div>

//       {/* Divider */}
//       <hr className="border-gray-200" />

//       {/* Price Range */}
//       <div>
//         <h3 className="font-black text-sm uppercase tracking-wide mb-4">
//           Price Range
//         </h3>
//         <div className="flex justify-between text-sm text-gray-600 mb-3">
//           <span>Rs. 0</span>
//           <span>Rs. 20,000+</span>
//         </div>
//         <input
//           type="range"
//           min="0"
//           max="20000"
//           defaultValue="20000"
//           className="w-full accent-primary cursor-pointer"
//         />
//       </div>

//       {/* Divider */}
//       <hr className="border-gray-200" />

//       {/* Bike Model */}
//       <div>
//         <h3 className="font-black text-sm uppercase tracking-wide mb-4">
//           Bike Model
//         </h3>
//         <div className="relative">
//           <select className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-500 outline-none appearance-none cursor-pointer bg-white">
//             <option value="">Select Bike Model</option>
//             <option value="cd70">Honda CD70</option>
//             <option value="125">Honda 125</option>
//             <option value="ybr">Yamaha YBR</option>
//             <option value="gs150">Suzuki GS150</option>
//           </select>
//           <ChevronDown
//             size={16}
//             className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
//           />
//         </div>
//       </div>

//     </div>
//   );
// }
// export default function ProductSidebar(){


// return (

// <div
// className="
// bg-white
// border
// rounded-xl
// p-6
// space-y-8
// "
// >


// <div>

// <h3
// className="
// font-black
// mb-5
// "
// >

// Categories

// </h3>


// {
// [
// "Engine Parts",
// "Brake Parts",
// "Electrical",
// "Accessories",
// "Tyres"
// ]
// .map(item=>(


// <label
// key={item}
// className="
// block
// mb-3
// text-sm
// "
// >


// <input
// type="checkbox"
// className="mr-2"
// />


// {item}


// </label>


// ))

// }


// </div>





// <div>

// <h3
// className="
// font-black
// mb-5
// "
// >

// Brands

// </h3>


// {
// [
// "Honda",
// "Yamaha",
// "Suzuki"
// ]
// .map(item=>(


// <label
// key={item}
// className="
// block
// mb-3
// text-sm
// "
// >


// <input
// type="checkbox"
// className="mr-2"
// />


// {item}


// </label>


// ))


// }


// </div>



// </div>

// )

// }