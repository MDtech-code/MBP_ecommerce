// components/product-detail/ProductGallery.jsx
import { useState } from "react";

export default function ProductGallery({ images }) {
  const [active, setActive] = useState(0);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">

      {/* Main Image */}
      <div className="h-80 flex items-center justify-center mb-6">
        <img
          src={images[active]}
          alt="product"
          className="max-h-full object-contain"
        />
      </div>

      {/* Thumbnails */}
      <div className="flex gap-3">
        {images.map((img, index) => (
          <button
            key={index}
            onClick={() => setActive(index)}
            className={`w-24 h-24 border-2 rounded-lg flex items-center justify-center p-2 transition
              ${active === index
                ? "border-primary"
                : "border-gray-200 hover:border-gray-300"
              }`}
          >
            <img
              src={img}
              alt={`thumb-${index}`}
              className="max-h-full object-contain"
            />
          </button>
        ))}
      </div>

    </div>
  );
}