import { useEffect, useState } from 'react'
import { fetchModelComparison } from '../api'
import { ms, pct } from '../components/ui/Metric'
import type { ModelComparisonItem } from '../types'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts'

export function ModelComparison() {
  const [models, setModels] = useState<ModelComparisonItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchModelComparison()
      .then(setModels)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-text-muted animate-pulse">Loading...</div>

  const radarData = models.map((m) => ({
    model: m.model_name,
    'Pass Rate': m.avg_pass_rate ? +(m.avg_pass_rate * 100).toFixed(1) : 0,
    'Low Hallucination': m.avg_hallucination_rate ? +(100 - m.avg_hallucination_rate * 100).toFixed(1) : 100,
    'Speed Score':
      m.avg_p95_latency_ms
        ? Math.max(0, +(100 - m.avg_p95_latency_ms / 100).toFixed(1))
        : 100,
  }))

  const colors = ['#3b82f6', '#22c55e', '#a855f7', '#eab308']

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Model Comparison</h1>
        <p className="text-sm text-text-muted">Performance comparison across evaluated models</p>
      </div>

      {models.length === 0 ? (
        <div className="card text-center text-text-muted py-12">
          No model data yet. Run evaluations with different models to compare.
        </div>
      ) : (
        <>
          <div className="card p-0 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-text-muted text-xs bg-bg-secondary border-b border-bg-border">
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Runs</th>
                  <th className="px-4 py-3">Avg Pass Rate</th>
                  <th className="px-4 py-3">Avg Hallucination</th>
                  <th className="px-4 py-3">Avg P95 Latency</th>
                  <th className="px-4 py-3">Avg Latency</th>
                </tr>
              </thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.model_name} className="table-row">
                    <td className="px-4 py-3 font-mono text-accent-blue">{m.model_name}</td>
                    <td className="px-4 py-3">{m.run_count}</td>
                    <td className="px-4 py-3 font-mono text-accent-green">{pct(m.avg_pass_rate)}</td>
                    <td className="px-4 py-3 font-mono text-accent-red">{pct(m.avg_hallucination_rate)}</td>
                    <td className="px-4 py-3 font-mono text-accent-cyan">{ms(m.avg_p95_latency_ms)}</td>
                    <td className="px-4 py-3 font-mono">{ms(m.avg_latency_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {radarData.length > 0 && (
            <div className="card">
              <h2 className="text-sm font-semibold text-text-primary mb-4">Capability Radar</h2>
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={[
                  { metric: 'Pass Rate', ...Object.fromEntries(models.map((m) => [m.model_name, m.avg_pass_rate ? +(m.avg_pass_rate * 100).toFixed(1) : 0])) },
                  { metric: 'Low Hallucination', ...Object.fromEntries(models.map((m) => [m.model_name, m.avg_hallucination_rate ? +(100 - m.avg_hallucination_rate * 100).toFixed(1) : 100])) },
                  { metric: 'Speed', ...Object.fromEntries(models.map((m) => [m.model_name, m.avg_p95_latency_ms ? Math.max(0, +(100 - m.avg_p95_latency_ms / 100).toFixed(1)) : 100])) },
                ]}>
                  <PolarGrid stroke="#1e1e2e" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 12, fill: '#94a3b8' }} />
                  {models.map((m, i) => (
                    <Radar key={m.model_name} name={m.model_name} dataKey={m.model_name} stroke={colors[i % colors.length]} fill={colors[i % colors.length]} fillOpacity={0.15} />
                  ))}
                  <Tooltip contentStyle={{ background: '#16161f', border: '1px solid #1e1e2e', fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  )
}
