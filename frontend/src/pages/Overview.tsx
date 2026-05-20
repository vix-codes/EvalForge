import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, Clock, TrendingUp } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { fetchAnalyticsSummary, fetchEvalRuns, fetchTrends } from '../api'
import { MetricCard, ms, pct } from '../components/ui/Metric'
import { StatusBadge, QualityGateBadge } from '../components/ui/Badge'
import type { AnalyticsSummary, EvalRunSummary, TrendDataPoint } from '../types'
import { usePolling } from '../hooks/usePolling'
import { format } from 'date-fns'

export function Overview() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null)
  const [recentRuns, setRecentRuns] = useState<EvalRunSummary[]>([])
  const [trends, setTrends] = useState<TrendDataPoint[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const [s, r, t] = await Promise.all([
        fetchAnalyticsSummary(),
        fetchEvalRuns({ page: 1, page_size: 8 }),
        fetchTrends({ days: 14 }),
      ])
      setSummary(s)
      setRecentRuns(r.items)
      setTrends(t)
    } catch {
      // silently handle
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])
  usePolling(load, 15000)

  if (loading) return <div className="text-text-muted animate-pulse">Loading...</div>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-text-primary">Overview</h1>
        <p className="text-sm text-text-muted mt-1">Platform health and evaluation summary</p>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Total Runs" value={summary?.total_runs ?? 0} />
        <MetricCard
          label="Avg Pass Rate"
          value={pct(summary?.avg_pass_rate)}
          color="text-accent-green"
        />
        <MetricCard
          label="Avg Hallucination Rate"
          value={pct(summary?.avg_hallucination_rate)}
          color={
            (summary?.avg_hallucination_rate ?? 0) > 0.15
              ? 'text-accent-red'
              : 'text-accent-yellow'
          }
        />
        <MetricCard
          label="Avg P95 Latency"
          value={ms(summary?.avg_p95_latency_ms)}
          color="text-accent-cyan"
        />
      </div>

      {trends.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-4">Pass Rate & Hallucination Trend (14d)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 11, fill: '#475569' }}
                tickFormatter={(v) => v.slice(5)}
              />
              <YAxis tick={{ fontSize: 11, fill: '#475569' }} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
              <Tooltip
                contentStyle={{ background: '#16161f', border: '1px solid #1e1e2e', fontSize: 12 }}
                formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="pass_rate" stroke="#22c55e" name="Pass Rate" dot={false} strokeWidth={2} />
              <Line type="monotone" dataKey="hallucination_rate" stroke="#ef4444" name="Hallucination Rate" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-sm font-semibold text-text-primary">Recent Eval Runs</h2>
          <Link to="/evals" className="text-xs text-accent-blue hover:underline">View all</Link>
        </div>
        {recentRuns.length === 0 ? (
          <p className="text-text-muted text-sm">No evaluation runs yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted text-xs border-b border-bg-border">
                <th className="pb-2 pr-4">Model</th>
                <th className="pb-2 pr-4">Status</th>
                <th className="pb-2 pr-4">Pass Rate</th>
                <th className="pb-2 pr-4">Hallucination</th>
                <th className="pb-2 pr-4">Gate</th>
                <th className="pb-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {recentRuns.map((run) => (
                <tr key={run.id} className="table-row">
                  <td className="py-2 pr-4">
                    <Link to={`/evals/${run.id}`} className="text-accent-blue hover:underline font-mono">
                      {run.model_name}
                    </Link>
                  </td>
                  <td className="py-2 pr-4"><StatusBadge status={run.status} /></td>
                  <td className="py-2 pr-4 text-accent-green">{pct(run.pass_rate)}</td>
                  <td className="py-2 pr-4 text-accent-red">{pct(run.hallucination_rate)}</td>
                  <td className="py-2 pr-4"><QualityGateBadge passed={run.quality_gate_passed} /></td>
                  <td className="py-2 text-text-muted text-xs">
                    {format(new Date(run.created_at), 'MMM d HH:mm')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {summary && summary.models_tested.length > 0 && (
        <div className="card">
          <h2 className="text-sm font-semibold text-text-primary mb-2">Models Tested</h2>
          <div className="flex flex-wrap gap-2">
            {summary.models_tested.map((m) => (
              <span key={m} className="badge badge-blue">{m}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
