// ProductToolbar.jsx
export default function ProductToolbar() {
  return (
    <div className="flex justify-between items-center mb-6">
      
      <p className="text-sm text-gray-600">
        Showing 1–12 of <span className="font-semibold">540 products</span>
      </p>

      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600 font-medium">Sort By:</span>
        <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm outline-none bg-white cursor-pointer">
          <option>Featured</option>
          <option>Price Low to High</option>
          <option>Price High to Low</option>
          <option>Newest First</option>
        </select>
      </div>

    </div>
  );
}
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