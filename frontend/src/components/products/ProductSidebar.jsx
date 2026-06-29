// ProductSidebar.jsx
import { ChevronDown } from "lucide-react";

const categories = [
  { name: "Engine Parts", count: 120 },
  { name: "Brake System", count: 85 },
  { name: "Electricals", count: 60 },
  { name: "Drive & Transmission", count: 75 },
  { name: "Body Parts", count: 95 },
  { name: "Accessories", count: 110 },
];

const brands = [
  { name: "Honda", count: 45 },
  { name: "Yamaha", count: 38 },
  { name: "Suzuki", count: 32 },
  { name: "Atlas Honda", count: 28 },
  { name: "Unique", count: 22 },
];

export default function ProductSidebar() {
  return (
    <div className="space-y-6">

      {/* Categories */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Categories
        </h3>
        <div className="space-y-2.5">
          {categories.map((item) => (
            <label
              key={item.name}
              className="flex items-center justify-between text-sm cursor-pointer group"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-gray-300 accent-primary cursor-pointer"
                />
                <span className="text-gray-700 group-hover:text-primary transition">
                  {item.name}
                </span>
              </div>
              <span className="text-gray-400 text-xs">({item.count})</span>
            </label>
          ))}
        </div>
      </div>

      {/* Divider */}
      <hr className="border-gray-200" />

      {/* Brand */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Brand
        </h3>
        <div className="space-y-2.5">
          {brands.map((item) => (
            <label
              key={item.name}
              className="flex items-center justify-between text-sm cursor-pointer group"
            >
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="w-4 h-4 rounded border-gray-300 accent-primary cursor-pointer"
                />
                <span className="text-gray-700 group-hover:text-primary transition">
                  {item.name}
                </span>
              </div>
              <span className="text-gray-400 text-xs">({item.count})</span>
            </label>
          ))}
        </div>
        <button className="text-primary text-sm font-semibold mt-3 hover:underline">
          View More +
        </button>
      </div>

      {/* Divider */}
      <hr className="border-gray-200" />

      {/* Price Range */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Price Range
        </h3>
        <div className="flex justify-between text-sm text-gray-600 mb-3">
          <span>Rs. 0</span>
          <span>Rs. 20,000+</span>
        </div>
        <input
          type="range"
          min="0"
          max="20000"
          defaultValue="20000"
          className="w-full accent-primary cursor-pointer"
        />
      </div>

      {/* Divider */}
      <hr className="border-gray-200" />

      {/* Bike Model */}
      <div>
        <h3 className="font-black text-sm uppercase tracking-wide mb-4">
          Bike Model
        </h3>
        <div className="relative">
          <select className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm text-gray-500 outline-none appearance-none cursor-pointer bg-white">
            <option value="">Select Bike Model</option>
            <option value="cd70">Honda CD70</option>
            <option value="125">Honda 125</option>
            <option value="ybr">Yamaha YBR</option>
            <option value="gs150">Suzuki GS150</option>
          </select>
          <ChevronDown
            size={16}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none"
          />
        </div>
      </div>

    </div>
  );
}
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