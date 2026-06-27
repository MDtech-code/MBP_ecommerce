export default function SourceBadge({ source }) {
  const config = {
    l1_memory: { color: 'bg-warning text-dark', icon: '⚡⚡', label: 'L1 Memory' },
    l2_redis: { color: 'bg-success', icon: '⚡', label: 'L2 Redis' },
    database: { color: 'bg-primary', icon: '🗄️', label: 'Database' },
  }
  const s = config[source] || config.database
  return <span className={`badge ${s.color}`}>{s.icon} {s.label}</span>
}
