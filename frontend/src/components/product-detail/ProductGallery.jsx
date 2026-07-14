// src/components/product-detail/ProductGallery.jsx
import { useState } from "react";

/**
 * ProductGallery
 *
 * Props:
 *   images: Array<{ id, image, is_primary, order }>
 *           from backend product.images[]
 *
 * Why images sorted before rendering:
 *   Backend returns images ordered by [order, created_at].
 *   Primary image is first by default from backend.
 *   We still find primary explicitly for initial active state
 *   so even if order changes it stays correct.
 */

const FALLBACK_IMG = "/placeholder-part.png";

export default function ProductGallery({ images = [] }) {
  // Find primary image index for initial active state
  const primaryIndex = images.findIndex((img) => img.is_primary);
  const [activeIndex, setActiveIndex] = useState(
    primaryIndex >= 0 ? primaryIndex : 0
  );

  // No images at all
  if (images.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="h-80 flex items-center justify-center mb-6
                        bg-gray-50 rounded-lg">
          <img
            src={FALLBACK_IMG}
            alt="No image available"
            className="max-h-full object-contain opacity-40"
          />
        </div>
      </div>
    );
  }

  const activeImage = images[activeIndex];

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6">

      {/* Main Image */}
      <div className="h-80 flex items-center justify-center mb-6">
        <img
          src={activeImage?.image || FALLBACK_IMG}
          alt="product"
          className="max-h-full object-contain"
          onError={(e) => { e.currentTarget.src = FALLBACK_IMG; }}
        />
      </div>

      {/* Thumbnails — only when multiple images */}
      {images.length > 1 && (
        <div className="flex gap-3 flex-wrap">
          {images.map((img, index) => (
            <button
              key={img.id}
              onClick={() => setActiveIndex(index)}
              className={`w-20 h-20 border-2 rounded-lg flex items-center
                          justify-center p-2 transition shrink-0
                          ${activeIndex === index
                            ? "border-primary"
                            : "border-gray-200 hover:border-gray-300"
                          }`}
            >
              <img
                src={img.image || FALLBACK_IMG}
                alt={`thumb-${index}`}
                className="max-h-full object-contain"
                onError={(e) => { e.currentTarget.src = FALLBACK_IMG; }}
              />
            </button>
          ))}
        </div>
      )}

    </div>
  );
}
