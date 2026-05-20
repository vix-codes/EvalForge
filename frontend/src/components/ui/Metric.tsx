interface MetricCardProps {
  label: string
  value: string | number | null
  unit?: string
  trend?: 'up' | 'down' | 'neutral'
  color?: string
}

export function MetricCard({ label, value, unit, color = 'text-text-primary' }: MetricCardProps) {
  return (
    <div className="card flex flex-col gap-1">
      <span className="text-xs text-text-muted uppercase tracking-wider">{label}</span>
      <span className={`text-2xl font-bold ${color}`}>
        {value === null || value === undefined ? '—' : value}
        {unit && value !== null && <span className="text-sm text-text-muted ml-1">{unit}</span>}
      </span>
    </div>
  )
}

export function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  return (v * 100).toFixed(1) + '%'
}

export function ms(v: number | null | undefined): string {
  if (v === null || v === undefined) return '—'
  if (v >= 1000) return (v / 1000).toFixed(2) + 's'
  return v.toFixed(0) + 'ms'
}
