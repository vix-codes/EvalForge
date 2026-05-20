import { useEffect, useState } from 'react'
import { fetchTrends, fetchModelComparison } from '../api'
import { MetricCard, ms, pct } from '../components/ui/Metric'
import type { ModelComparisonItem, TrendDataPoint } from '../types'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar,
} from 'recharts'

export function Analytics() {
  const [trends, setTrends] = useState<TrendDataPoint[]>([])
  const [models, setModels] = useState<ModelComparisonItem[]>([])
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [t, m] = await Promise.all([fetchTrends({ days }), fetchModelComparison()])
      setTrends(t)
      setModels(m)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [days])

  if (loading) return <div className="text-text-muted animate-pulse">Loading...</div>

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Analytics</h1>
          <p className="text-sm text-text-muted">Trend analysis and model metrics</p>
        </div>
        <div className="flex gap-2">
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`text-xs px-3 py-1 rounded border transition-colors ${days === d ? 'border-accent-blue text-accent-blue bg-accent-blue/10' : 'border-bg-border text-text-muted'}`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {trends.length > 0 ? (
        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Evaluation Trends ({days}d)</h2>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#475569' }} tickFormatter={(v) => v.slice(5)} />
              <YAxis yAxisId="rate" tick={{ fontSize: 11, fill: '#475569' }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
              <YAxis yAxisId="latency" orientation="right" tick={{ fontSize: 11, fill: '#475569' }} tickFormatter={(v) => `${v}ms`} />
              <Tooltip
                contentStyle={{ background: '#16161f', border: '1px solid #1e1e2e', fontSize: 12 }}
                formatter={(v: number, name: string) =>
                  name.includes('latency') ? `${v.toFixed(0)}ms` : `${(v * 100).toFixed(1)}%`
                }
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line yAxisId="rate" type="monotone" dataKey="pass_rate" stroke="#22c55e" name="Pass Rate" dot={false} strokeWidth={2} />
              <Line yAxisId="rate" type="monotone" dataKey="hallucination_rate" stroke="#ef4444" name="Hallucination" dot={false} strokeWidth={2} />
              <Line yAxisId="latency" type="monotone" dataKey="p95_latency_ms" stroke="#06b6d4" name="P95 Latency" dot={false} strokeWidth={2} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="card text-center text-text-muted py-8">No trend data yet. Run evaluations to generate analytics.</div>
      )}

      {models.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Model Pass Rate Comparison</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={models} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" horizontal={false} />
              <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 11, fill: '#475569' }} />
              <YAxis type="category" dataKey="model_name" tick={{ fontSize: 11, fill: '#94a3b8' }} width={100} />
              <Tooltip
                contentStyle={{ background: '#16161f', border: '1px solid #1e1e2e', fontSize: 12 }}
                formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              />
              <Bar dataKey="avg_pass_rate" fill="#3b82f6" name="Avg Pass Rate" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
