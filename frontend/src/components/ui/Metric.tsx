import { TrendingDown, TrendingUp } from 'lucide-react'

interface MetricCardProps {
  label: string
  value: string | number | null
  sub?: string
  icon?: React.ReactNode
  trend?: number       // positive = good, negative = bad
  trendLabel?: string
  color?: string
  glow?: boolean
}

export function MetricCard({ label, value, sub, icon, trend, trendLabel, color = 'text-white', glow }: MetricCardProps) {
  return (
    <div className={glow ? 'card-glow' : 'card'} style={{ transition: 'box-shadow 0.3s' }}>
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-widest">{label}</span>
        {icon && <span className="text-slate-600">{icon}</span>}
      </div>
      <div className={`text-2xl font-bold font-mono tracking-tight ${color}`}>
        {value === null || value === undefined ? <span className="text-slate-600">—</span> : value}
        {sub && value !== null && <span className="text-sm text-slate-500 font-sans ml-1">{sub}</span>}
      </div>
      {trend !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-xs ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          <span>{trendLabel || `${Math.abs(trend).toFixed(1)}%`}</span>
        </div>
      )}
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

export function ScoreBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="progress-bar w-full">
      <div className={`progress-fill ${color}`} style={{ width: `${Math.min(100, value * 100)}%` }} />
    </div>
  )
}
