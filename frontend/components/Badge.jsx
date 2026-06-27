export default function Badge({ text, variant = 'primary' }) {
  return <span className={`badge bg-${variant} me-1`}>{text}</span>
}