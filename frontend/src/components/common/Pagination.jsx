// Pagination.jsx
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ currentPage = 1, totalPages = 45 }) {
  const pages = [1, 2, 3, 4, 5];

  return (
    <div className="flex items-center justify-center gap-1 mt-10">
      
      {/* Prev */}
      <button className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 text-gray-500 hover:border-primary hover:text-primary transition disabled:opacity-40">
        <ChevronLeft size={16} />
      </button>

      {/* Page Numbers */}
      {pages.map((page) => (
        <button
          key={page}
          className={`w-9 h-9 flex items-center justify-center rounded-lg text-sm font-semibold transition
            ${
              page === currentPage
                ? "bg-primary text-white"
                : "border border-gray-300 text-gray-700 hover:border-primary hover:text-primary"
            }
          `}
        >
          {page}
        </button>
      ))}

      {/* Ellipsis */}
      <span className="w-9 h-9 flex items-center justify-center text-gray-400 text-sm">
        ...
      </span>

      {/* Last Page */}
      <button className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 text-sm font-semibold text-gray-700 hover:border-primary hover:text-primary transition">
        {totalPages}
      </button>

      {/* Next */}
      <button className="w-9 h-9 flex items-center justify-center rounded-lg border border-gray-300 text-gray-500 hover:border-primary hover:text-primary transition">
        <ChevronRight size={16} />
      </button>

    </div>
  );
}