// src/components/layout/megamenu/BikePartsMegaMenu.jsx
import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Bike } from "lucide-react";
import { useCategoriesTree } from "@entities/product"

/**
 * BikePartsMegaMenu
 *
 * 3-panel hover mega menu driven by live category tree from backend.
 *
 * Panel 1: Root categories (level 0)
 * Panel 2: Children of hovered root (level 1)
 * Panel 3: Children of hovered level-1 + "Need Help?" CTA
 *
 * Data shape (from backend tree response):
 *   { id, name, slug, children: [...] }
 *
 * Navigation:
 *   Clicking any category → /product?category=<slug>
 */
export default function BikePartsMegaMenu({ onClose }) {
  const { data: categories = [], isLoading } = useCategoriesTree();

  // Which root category is hovered → drives panel 2
  const [activeRoot, setActiveRoot] = useState(null);
  // Which level-1 category is hovered → drives panel 3
  const [activeSub, setActiveSub] = useState(null);

  // Initialize activeRoot to first category on load
  const rootCategories = categories;
  const effectiveRoot = activeRoot ?? rootCategories[0] ?? null;
  const subCategories = effectiveRoot?.children ?? [];
  const effectiveSub = activeSub ?? subCategories[0] ?? null;
  const subSubCategories = effectiveSub?.children ?? [];

  // Count helpers for footer
  const totalRoots = rootCategories.length;
  const totalSubs  = rootCategories.reduce(
    (acc, cat) => acc + (cat.children?.length ?? 0), 0
  );

  if (isLoading) {
    return (
      <div className="absolute top-full left-1/2 -translate-x-1/2 w-225
                      bg-white border border-gray-200 shadow-2xl rounded-b-xl
                      z-50 p-8 flex items-center justify-center">
        <span className="loading loading-spinner loading-md text-primary" />
      </div>
    );
  }

  return (
    <div
      className="absolute top-full left-1/2 -translate-x-1/2 w-240
                 bg-white border border-gray-200 shadow-2xl rounded-b-xl z-50
                 flex flex-col"
      onMouseLeave={onClose}
    >
      {/* ── 3 Panels ──────────────────────────────────────────────────────── */}
      <div className="flex min-h-95">

        {/* Panel 1 — Root Categories */}
        <div className="w-56 border-r border-gray-100 py-3 shrink-0">
          {rootCategories.map((cat) => {
            const isActive = effectiveRoot?.id === cat.id;
            return (
              <button
                key={cat.id}
                onMouseEnter={() => {
                  setActiveRoot(cat);
                  setActiveSub(null);
                }}
                className={`w-full flex items-center justify-between px-4 py-2.5
                            text-sm font-semibold transition-colors text-left
                            ${isActive
                              ? "text-primary bg-red-50 border-r-2 border-primary"
                              : "text-gray-700 hover:text-primary hover:bg-gray-50"
                            }`}
              >
                <span>{cat.name}</span>
                {cat.children?.length > 0 && (
                  <ChevronRight size={14} className="shrink-0" />
                )}
              </button>
            );
          })}

          {/* View All */}
          <div className="px-4 pt-3 mt-2 border-t border-gray-100">
            <Link
              to="/product"
              onClick={onClose}
              className="text-primary text-sm font-semibold
                         flex items-center gap-1 hover:underline"
            >
              View All Categories →
            </Link>
          </div>
        </div>

        {/* Panel 2 — Subcategories */}
        <div className="w-52 border-r border-gray-100 py-3 shrink-0">
          {subCategories.length === 0 ? (
            <div className="px-4 py-4 text-sm text-gray-400">
              No subcategories
            </div>
          ) : (
            subCategories.map((sub) => {
              const isActive = effectiveSub?.id === sub.id;
              return (
                <button
                  key={sub.id}
                  onMouseEnter={() => setActiveSub(sub)}
                  className={`w-full flex items-center justify-between px-4 py-2.5
                              text-sm transition-colors text-left
                              ${isActive
                                ? "text-primary bg-red-50 font-semibold"
                                : "text-gray-600 hover:text-primary hover:bg-gray-50"
                              }`}
                >
                  <span>{sub.name}</span>
                  {sub.children?.length > 0 && (
                    <ChevronRight size={13} className="shrink-0 text-gray-400" />
                  )}
                </button>
              );
            })
          )}
        </div>

        {/* Panel 3 — Sub-subcategories + CTA */}
        <div className="flex flex-1 gap-0">

          {/* Sub-subcategory list */}
          <div className="flex-1 py-3 px-2">
            {subSubCategories.length === 0 && effectiveSub ? (
              // Leaf node — direct link to this category's products
              <Link
                to={`/product?category=${effectiveSub.slug}`}
                onClick={onClose}
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg
                           text-sm text-gray-600 hover:bg-gray-50
                           hover:text-primary transition-colors"
              >
                <span className="w-10 h-10 rounded-full bg-gray-100
                                 flex items-center justify-center shrink-0">
                  <Bike size={18} className="text-gray-400" />
                </span>
                <span>
                  Browse {effectiveSub.name}
                </span>
                <ChevronRight size={14} className="ml-auto text-gray-400" />
              </Link>
            ) : (
              subSubCategories.map((subsub) => (
                <Link
                  key={subsub.id}
                  to={`/product?category=${subsub.slug}`}
                  onClick={onClose}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-lg
                             text-sm text-gray-600 hover:bg-gray-50
                             hover:text-primary transition-colors group"
                >
                  <span className="w-10 h-10 rounded-full bg-gray-100
                                   flex items-center justify-center shrink-0
                                   group-hover:bg-red-50 transition-colors">
                    <Bike size={18} className="text-gray-400 group-hover:text-primary" />
                  </span>
                  <span>{subsub.name}</span>
                  <ChevronRight size={14} className="ml-auto text-gray-400" />
                </Link>
              ))
            )}
          </div>

          {/* CTA Card */}
          <div className="w-52 p-4 shrink-0">
            <div className="bg-gray-50 rounded-xl p-4 h-full flex flex-col
                            items-center justify-center text-center border
                            border-gray-200">
              <p className="font-black text-gray-900 text-sm leading-tight">
                Need Help Finding Parts?
              </p>
              <p className="text-xs text-gray-500 mt-1 mb-4">
                Browse by Bike Model
              </p>
              <Link
                to="/product"
                onClick={onClose}
                className="bg-primary text-white text-xs font-bold
                           px-4 py-2 rounded-lg hover:bg-red-700
                           transition flex items-center gap-1"
              >
                Select Bike →
              </Link>
            </div>
          </div>

        </div>
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <div className="border-t border-gray-100 px-6 py-3 flex items-center
                      justify-end gap-2 text-xs text-gray-500">
        <span>{totalRoots} Categories</span>
        <span className="text-primary font-bold">•</span>
        <span>{totalSubs} Sub Categories</span>
      </div>
    </div>
  );
}