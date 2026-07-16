// src/components/layout/megamenu/BrandsMegaMenu.jsx
import { Link } from "react-router-dom";
import { ShieldCheck, WalletCards, Truck, RotateCcw, Lock } from "lucide-react";
import { useBrands, useCategoriesTree } from "../../../entities/product/api/useProductQueries";
import { getMediaUrl } from "../../../shared/lib/media";

/**
 * BrandsMegaMenu
 *
 * 3-panel mega menu:
 *   Panel 1: Category list + "Select Bike" CTA
 *   Panel 2: Popular brands grid (logo + name)
 *   Panel 3: "100% Genuine" promo card
 *
 * Footer: 5 trust badges + "Looking for a brand?" strip
 *
 * Brands come from /api/products/brands/ — logo is a relative path
 * so we pass it through getMediaUrl() same as avatar pattern.
 */

const TRUST_BADGES = [
  { icon: ShieldCheck, label: "100% Genuine Parts" },
  { icon: WalletCards, label: "Best Prices" },
  { icon: Truck,       label: "Fast Delivery" },
  { icon: RotateCcw,   label: "Easy Returns" },
  { icon: Lock,        label: "Secure Payments" },
];

// Show max 14 brands in grid — last cell is "View All"
const MAX_GRID_BRANDS = 14;

export default function BrandsMegaMenu({ onClose }) {
  const { data: brands = [],     isLoading: brandsLoading }     = useBrands();
  const { data: categories = [], isLoading: categoriesLoading } = useCategoriesTree();

  const isLoading = brandsLoading || categoriesLoading;

  if (isLoading) {
    return (
      <div className="absolute top-full left-1/2 -translate-x-1/2 w-240
                      bg-white border border-gray-200 shadow-2xl rounded-b-xl
                      z-50 p-8 flex items-center justify-center">
        <span className="loading loading-spinner loading-md text-primary" />
      </div>
    );
  }

  const gridBrands = brands.slice(0, MAX_GRID_BRANDS);
  const hasMore    = brands.length > MAX_GRID_BRANDS;

  return (
    <div
      className="absolute top-full left-1/2 -translate-x-1/2 w-240
                 bg-white border border-gray-200 shadow-2xl rounded-b-xl
                 z-50 flex flex-col"
      onMouseLeave={onClose}
    >

      {/* ── 3 Panels ──────────────────────────────────────────────────────── */}
      <div className="flex min-h-105">

        {/* Panel 1 — Category list + CTA */}
        <div className="w-56 border-r border-gray-100 py-4 shrink-0
                        flex flex-col">
          <p className="px-4 text-xs font-black text-gray-400 uppercase
                        tracking-widest mb-2">
            Shop By Category
          </p>

          <div className="flex-1">
            {categories.map((cat) => (
              <Link
                key={cat.id}
                to={`/product?category=${cat.slug}`}
                onClick={onClose}
                className="flex items-center justify-between px-4 py-2.5
                           text-sm text-gray-600 hover:text-primary
                           hover:bg-gray-50 transition-colors font-medium"
              >
                {cat.name}
                <span className="text-gray-300">›</span>
              </Link>
            ))}
          </div>

          {/* Select Bike CTA */}
          <div className="mx-3 mt-3 p-3 bg-gray-50 rounded-xl border
                          border-gray-200">
            <p className="text-xs font-bold text-gray-800">
              Not sure what you need?
            </p>
            <p className="text-xs text-gray-500 mt-0.5 mb-2">
              Browse by your bike model
            </p>
            <Link
              to="/product"
              onClick={onClose}
              className="text-primary text-xs font-bold
                         hover:underline flex items-center gap-1"
            >
              Select Bike →
            </Link>
          </div>
        </div>

        {/* Panel 2 — Brands grid */}
        <div className="flex-1 p-4">
          <p className="text-xs font-black text-gray-400 uppercase
                        tracking-widest mb-3">
            Popular Brands
          </p>

          <div className="grid grid-cols-5 gap-2">
            {gridBrands.map((brand) => (
              <Link
                key={brand.id}
                to={`/product?brand=${brand.slug}`}
                onClick={onClose}
                className="flex flex-col items-center gap-1.5 p-2.5
                           border border-gray-200 rounded-xl
                           hover:border-primary hover:shadow-sm
                           transition-all group"
              >
                {brand.logo ? (
                  <img
                    src={getMediaUrl(brand.logo)}
                    alt={brand.name}
                    className="h-10 w-full object-contain"
                    onError={(e) => { e.target.style.display = "none"; }}
                  />
                ) : (
                  <div className="h-10 w-full flex items-center justify-center">
                    <span className="text-xs font-black text-gray-400">
                      {brand.name[0]}
                    </span>
                  </div>
                )}
                <span className="text-xs font-semibold text-gray-700
                                 group-hover:text-primary transition-colors
                                 text-center leading-tight">
                  {brand.name}
                </span>
              </Link>
            ))}

            {/* View All Brands cell */}
            {hasMore && (
              <Link
                to="/product"
                onClick={onClose}
                className="flex flex-col items-center justify-center gap-1
                           p-2.5 border border-dashed border-gray-300
                           rounded-xl hover:border-primary
                           hover:text-primary transition-all text-center"
              >
                <span className="text-xs font-bold text-primary">
                  View All Brands →
                </span>
              </Link>
            )}
          </div>
        </div>

        {/* Panel 3 — Promo card */}
        <div className="w-48 p-4 shrink-0 border-l border-gray-100
                        flex flex-col gap-3">
          <div className="bg-gray-50 rounded-xl p-4 flex-1 flex flex-col
                          justify-center border border-gray-200">
            <p className="text-xs font-black text-gray-500 uppercase
                          tracking-wide">
              100% Genuine
            </p>
            <p className="text-base font-black text-gray-900 mt-1 leading-tight">
              Trusted Brands
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Original quality parts for your motorcycle
            </p>
          </div>
        </div>

      </div>

      {/* ── Trust badges ───────────────────────────────────────────────────── */}
      <div className="border-t border-gray-100 px-6 py-3
                      flex items-center justify-between">
        {TRUST_BADGES.map(({ icon: Icon, label }) => (
          <div key={label} className="flex items-center gap-1.5 text-xs
                                     text-gray-600">
            <Icon size={14} className="text-gray-500 shrink-0" />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* ── Bottom strip ───────────────────────────────────────────────────── */}
      <div className="border-t border-gray-100 bg-gray-50 px-6 py-3
                      flex items-center justify-between rounded-b-xl">
        <div>
          <p className="text-sm font-bold text-gray-800">
            Looking for a specific brand?
          </p>
          <p className="text-xs text-gray-500">
            Can't find your brand in the list?
          </p>
        </div>
        <button className="border border-primary text-primary text-xs
                           font-bold px-4 py-2 rounded-lg
                           hover:bg-primary hover:text-white transition">
          Request a Brand →
        </button>
      </div>

    </div>
  );
}