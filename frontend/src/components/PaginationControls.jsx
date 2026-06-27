export default function PaginationControls({ meta, onPageChange }) {
  if (!meta || meta.total_pages <= 1) return null
  return (
    <div className="flex items-center gap-2 mt-3">
      <button
        className="btn btn-sm btn-outline-secondary"
        disabled={meta.page <= 1}
        onClick={() => onPageChange(meta.page - 1)}
      >
        ← Prev
      </button>
      <span className="text-sm text-gray-600">
        Page {meta.page} of {meta.total_pages} ({meta.total_items} total)
      </span>
      <button
        className="btn btn-sm btn-outline-secondary"
        disabled={meta.page >= meta.total_pages}
        onClick={() => onPageChange(meta.page + 1)}
      >
        Next →
      </button>
    </div>
  )
}
