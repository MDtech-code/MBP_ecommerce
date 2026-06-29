// ProductGrid.jsx
import ProductCard from "./ProductCard";

export default function ProductGrid({ products }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
// import ProductCard from "./ProductCard";


// export default function ProductGrid({
// products
// }){


// return (

// <div
// className="
// grid
// grid-cols-2
// lg:grid-cols-3
// xl:grid-cols-4
// gap-6
// "
// >


// {
// products.map(product=>(

// <ProductCard

// key={product.id}

// product={product}

// />

// ))

// }


// </div>

// )

// }