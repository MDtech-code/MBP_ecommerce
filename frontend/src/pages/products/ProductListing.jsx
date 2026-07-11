// ProductListing.jsx (page)
import Header from "../../components/layout/Header";
import ProductSidebar from "../../components/products/ProductSidebar";
import ProductGrid from "../../components/products/ProductGrid";
import ProductToolbar from "../../components/products/ProductToolbar";
import Pagination from "../../components/common/Pagination";
import { products } from "../../data/products";

export default function ProductListing() {
  return (
    <>
      <Header/>

      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Breadcrumb */}
          <nav className="text-sm text-gray-500 mb-6 flex items-center gap-2">
            <span className="hover:text-primary cursor-pointer">Home</span>
            <span>›</span>
            <span className="text-gray-800 font-medium">All Products</span>
          </nav>

          {/* Main Layout */}
          <div className="flex gap-8">

            {/* Sidebar */}
            <aside className="w-64 shrink-0">
              <ProductSidebar />
            </aside>

            {/* Content */}
            <div className="flex-1">
              <ProductToolbar />
              <ProductGrid products={products} />
              <Pagination currentPage={1} totalPages={45} />
            </div>

          </div>
        </div>
      </div>
    </>
  );
}
// import AccountHeader from "../../components/account/AccountHeader";

// import ProductSidebar from "../../components/products/ProductSidebar";

// import ProductGrid from "../../components/products/ProductGrid";

// import ProductToolbar from "../../components/products/ProductToolbar";


// import {
// products
// } from "../../data/products";



// export default function ProductListing(){


// return (

// <>


// <AccountHeader />


// <div
// className="
// bg-surface
// min-h-screen
// "
// >


// <div
// className="
// max-w-360
// mx-auto
// px-6
// py-10
// "
// >


// <h1
// className="
// text-4xl
// font-black
// mb-8
// "
// >

// Bike Parts

// </h1>



// <div
// className="
// grid
// lg:grid-cols-4
// gap-8
// "
// >


// <div>

// <ProductSidebar />

// </div>



// <div
// className="
// lg:col-span-3
// "
// >


// <ProductToolbar/>


// <ProductGrid

// products={products}

// />



// </div>


// </div>



// </div>


// </div>


// </>

// )

// }