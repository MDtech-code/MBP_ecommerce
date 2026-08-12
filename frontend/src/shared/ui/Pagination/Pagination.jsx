// src/shared/ui/Pagination.jsx
import { ChevronLeft, ChevronRight } from "lucide-react";


export default function Pagination({
  currentPage = 1,
  totalPages  = 1,
  hasNext     = false,
  hasPrevious = false,
  onPageChange,
}) {
  if (totalPages <= 1) return null;

  // ── Build page window (up to 5 pages centered on currentPage) ─────────────
  const WINDOW = 5;
  let start = Math.max(1, currentPage - Math.floor(WINDOW / 2));
  let end   = start + WINDOW - 1;

  if (end > totalPages) {
    end   = totalPages;
    start = Math.max(1, end - WINDOW + 1);
  }

  const pages = [];
  for (let i = start; i <= end; i++) pages.push(i);

  const showEllipsis = end < totalPages - 1;
  const showLast     = end < totalPages;

  const handlePage = (page) => {
    if (page < 1 || page > totalPages || page === currentPage) return;
    onPageChange?.(page);
    // Scroll to top on page change
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="flex items-center justify-center gap-1 mt-10">

      {/* Prev */}
      <button
        onClick={() => handlePage(currentPage - 1)}
        disabled={!hasPrevious}
        className="w-9 h-9 flex items-center justify-center rounded-lg
                   border border-gray-300 text-gray-500
                   hover:border-primary hover:text-primary
                   transition disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <ChevronLeft size={16} />
      </button>

      {/* Page window */}
      {pages.map((page) => (
        <button
          key={page}
          onClick={() => handlePage(page)}
          className={`w-9 h-9 flex items-center justify-center rounded-lg
                      text-sm font-semibold transition
                      ${page === currentPage
                        ? "bg-primary text-white"
                        : "border border-gray-300 text-gray-700 hover:border-primary hover:text-primary"
                      }`}
        >
          {page}
        </button>
      ))}

      {/* Ellipsis */}
      {showEllipsis && (
        <span className="w-9 h-9 flex items-center justify-center
                         text-gray-400 text-sm">
          ...
        </span>
      )}

      {/* Last page — only when outside window */}
      {showLast && (
        <button
          onClick={() => handlePage(totalPages)}
          className="w-9 h-9 flex items-center justify-center rounded-lg
                     border border-gray-300 text-sm font-semibold
                     text-gray-700 hover:border-primary
                     hover:text-primary transition"
        >
          {totalPages}
        </button>
      )}

      {/* Next */}
      <button
        onClick={() => handlePage(currentPage + 1)}
        disabled={!hasNext}
        className="w-9 h-9 flex items-center justify-center rounded-lg
                   border border-gray-300 text-gray-500
                   hover:border-primary hover:text-primary
                   transition disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <ChevronRight size={16} />
      </button>

    </div>
  );
}
