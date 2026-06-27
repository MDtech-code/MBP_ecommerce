export default function Card({ title, children, className = '' }) {
  return (
    <div className={`card shadow-sm mb-4 ${className}`}>
      <div className="card-header fw-bold">{title}</div>
      <div className="card-body">{children}</div>
    </div>
  )
}
