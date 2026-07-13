import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity, AlertTriangle, CheckCircle2, Clock,
  ShieldCheck, TrendingUp, Zap, BarChart2
} from 'lucide-react'
import {
  AreaChart, Area, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { fetchAnalyticsSummary, fetchEvalRuns, fetchTrends } from '../api'
import { MetricCard, ScoreBar, ms, pct } from '../components/ui/Metric'
import { StatusBadge, QualityGateBadge } from '../components/ui/Badge'
import type { AnalyticsSummary, EvalRunSummary, TrendDataPoint } from '../types'
import { usePolling } from '../hooks/usePolling'
import { format } from 'date-fns'

const CHART_STYLE = {
  background: 'transparent',
  border: '1px solid rgba(255,255,255,0.05)',
  borderRadius: 10,
  fontSize: 11,
  color: '#64748b',
}

function SkeletonCard() {
  return <div className="card h-24 skeleton" />
}

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
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])
  usePolling(load, 10000)

  const hasRunning = recentRuns.some(r => r.status === 'running' || r.status === 'pending')

  return (
    <div className="space-y-6 animate-fade-in">

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Overview</h1>
          <p className="text-sm text-slate-500 mt-0.5">Platform health · real-time evaluation dashboard</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {hasRunning
            ? <><span className="pulse-dot" /><span className="text-emerald-400">Evaluation running</span></>
            : <><Activity className="w-3.5 h-3.5" /><span>Auto-refresh 10s</span></>
          }
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-4 gap-4">
        {loading ? (
          <>
            <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
          </>
        ) : (
          <>
            <MetricCard
              label="Total Runs"
              value={summary?.total_runs ?? 0}
              icon={<Activity className="w-4 h-4" />}
              glow
            />
            <MetricCard
              label="Avg Pass Rate"
              value={pct(summary?.avg_pass_rate)}
              icon={<CheckCircle2 className="w-4 h-4" />}
              color={(summary?.avg_pass_rate ?? 0) >= 0.8 ? 'text-emerald-400' : 'text-amber-400'}
            />
            <MetricCard
              label="Hallucination Rate"
              value={pct(summary?.avg_hallucination_rate)}
              icon={<AlertTriangle className="w-4 h-4" />}
              color={(summary?.avg_hallucination_rate ?? 0) > 0.15 ? 'text-red-400' : 'text-emerald-400'}
            />
            <MetricCard
              label="Avg P95 Latency"
              value={ms(summary?.avg_p95_latency_ms)}
              icon={<Clock className="w-4 h-4" />}
              color="text-cyan-400"
            />
          </>
        )}
      </div>

      {/* Charts row */}
      {trends.length > 0 && (
        <div className="grid grid-cols-3 gap-4">
          {/* Pass + hallucination trend */}
          <div className="card col-span-2">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-semibold text-white">Quality Trend</h2>
                <p className="text-xs text-slate-500 mt-0.5">Pass rate & hallucination — last 14 days</p>
              </div>
              <TrendingUp className="w-4 h-4 text-slate-600" />
            </div>
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={trends} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="passGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="hallGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#475569' }} tickFormatter={v => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: '#475569' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
                <Tooltip
                  contentStyle={CHART_STYLE}
                  labelStyle={{ color: '#94a3b8' }}
                  formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
                />
                <Legend wrapperStyle={{ fontSize: 11, color: '#64748b' }} />
                <Area type="monotone" dataKey="pass_rate" stroke="#6366f1" fill="url(#passGrad)" name="Pass Rate" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="hallucination_rate" stroke="#ef4444" fill="url(#hallGrad)" name="Hallucination" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Quality gate summary */}
          <div className="card flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Quality Gates</h2>
              <ShieldCheck className="w-4 h-4 text-slate-600" />
            </div>
            {summary && (
              <div className="space-y-4 flex-1">
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-500">Pass Rate</span>
                    <span className="text-white font-mono">{pct(summary.avg_pass_rate)}</span>
                  </div>
                  <ScoreBar value={summary.avg_pass_rate ?? 0} color="bg-indigo-500" />
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-500">Hallucination</span>
                    <span className="text-white font-mono">{pct(summary.avg_hallucination_rate)}</span>
                  </div>
                  <ScoreBar value={summary.avg_hallucination_rate ?? 0} color="bg-red-500" />
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-slate-500">Models Tested</span>
                    <span className="text-white font-mono">{summary.models_tested?.length ?? 0}</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {summary.models_tested?.slice(0, 4).map(m => (
                      <span key={m} className="badge-purple text-[10px]">
                        <Zap className="w-2.5 h-2.5" />{m}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent runs table */}
      <div className="card">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-slate-600" />
            <h2 className="text-sm font-semibold text-white">Recent Eval Runs</h2>
          </div>
          <Link to="/evals" className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors flex items-center gap-1">
            View all →
          </Link>
        </div>

        {loading ? (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => <div key={i} className="skeleton h-9 rounded-md" />)}
          </div>
        ) : recentRuns.length === 0 ? (
          <div className="text-center py-12">
            <Activity className="w-8 h-8 text-slate-700 mx-auto mb-3" />
            <p className="text-slate-500 text-sm">No evaluation runs yet.</p>
            <p className="text-slate-600 text-xs mt-1">Trigger your first run to see results here.</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-white/5">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-600 uppercase tracking-wider bg-white/[0.02] border-b border-white/5">
                  <th className="px-4 py-3">Model</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Pass Rate</th>
                  <th className="px-4 py-3">Hallucination</th>
                  <th className="px-4 py-3">P95</th>
                  <th className="px-4 py-3">Gate</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map((run, i) => (
                  <tr key={run.id} className="table-row" style={{ animationDelay: `${i * 40}ms` }}>
                    <td className="px-4 py-3">
                      <Link to={`/evals/${run.id}`} className="text-indigo-400 hover:text-indigo-300 font-mono text-xs transition-colors">
                        {run.model_name}
                      </Link>
                    </td>
                    <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
                    <td className="px-4 py-3">
                      <span className={`font-mono text-xs ${(run.pass_rate ?? 0) >= 0.8 ? 'text-emerald-400' : 'text-amber-400'}`}>
                        {pct(run.pass_rate)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-mono text-xs ${(run.hallucination_rate ?? 0) === 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {pct(run.hallucination_rate)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-cyan-400">{ms(run.p95_latency_ms)}</td>
                    <td className="px-4 py-3"><QualityGateBadge passed={run.quality_gate_passed} /></td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {format(new Date(run.created_at), 'MMM d · HH:mm')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
