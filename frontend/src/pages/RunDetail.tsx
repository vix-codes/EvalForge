import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import { format } from 'date-fns'
import { fetchEvalRun, fetchRunResults, fetchFailureBreakdown } from '../api'
import { MetricCard, ms, pct } from '../components/ui/Metric'
import { StatusBadge, QualityGateBadge, PassBadge } from '../components/ui/Badge'
import type { EvalRun, EvalResult } from '../types'
import { usePolling } from '../hooks/usePolling'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = ['#22c55e', '#ef4444', '#eab308', '#3b82f6']

export function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<EvalRun | null>(null)
  const [results, setResults] = useState<EvalResult[]>([])
  const [failures, setFailures] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [resultPage, setResultPage] = useState(1)
  const [resultTotal, setResultTotal] = useState(0)
  const [filterPassed, setFilterPassed] = useState<boolean | undefined>(undefined)

  const load = async () => {
    if (!id) return
    try {
      const [r, res] = await Promise.all([
        fetchEvalRun(id),
        fetchRunResults(id, { page: resultPage, page_size: 30, passed: filterPassed }),
      ])
      setRun(r)
      setResults(res.items)
      setResultTotal(res.total)
      if (r.status === 'completed') {
        const fb = await fetchFailureBreakdown(id)
        setFailures(fb)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id, resultPage, filterPassed])
  usePolling(load, 5000, run?.status === 'running' || run?.status === 'pending')

  if (loading) return <div className="text-text-muted animate-pulse">Loading...</div>
  if (!run) return <div className="text-accent-red">Run not found</div>

  const failureData = Object.entries(failures).map(([k, v]) => ({ name: k, value: v }))

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/evals" className="text-text-muted hover:text-text-primary">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-text-primary font-mono">{run.model_name}</h1>
          <p className="text-xs text-text-muted">
            {format(new Date(run.created_at), 'PPpp')} · trigger: {run.trigger}
            {run.commit_sha && ` · ${run.commit_sha.slice(0, 8)}`}
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          <StatusBadge status={run.status} />
          <QualityGateBadge passed={run.quality_gate_passed} />
        </div>
      </div>

      {run.error_message && (
        <div className="card border-accent-red/30 text-accent-red text-sm">
          <AlertTriangle className="w-4 h-4 inline mr-2" />
          {run.error_message}
        </div>
      )}

      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Pass Rate" value={pct(run.pass_rate)} color="text-accent-green" />
        <MetricCard label="Hallucination Rate" value={pct(run.hallucination_rate)} color="text-accent-red" />
        <MetricCard label="P95 Latency" value={ms(run.p95_latency_ms)} color="text-accent-cyan" />
        <MetricCard label="Avg Latency" value={ms(run.avg_latency_ms)} />
      </div>

      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Total Questions" value={run.total_questions} />
        <MetricCard label="Passed" value={run.passed_count} color="text-accent-green" />
        <MetricCard label="Failed" value={run.failed_count} color="text-accent-red" />
        <MetricCard label="Hallucinations" value={run.hallucination_count} color="text-accent-yellow" />
      </div>

      {failureData.length > 0 && (
        <div className="grid grid-cols-2 gap-4">
          <div className="card">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Failure Breakdown</h3>
            <div className="space-y-2">
              {failureData.map(({ name, value }) => (
                <div key={name} className="flex justify-between text-sm">
                  <span className="text-text-secondary font-mono text-xs">{name}</span>
                  <span className="text-accent-red">{value}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <h3 className="text-sm font-semibold text-text-primary mb-3">Failure Distribution</h3>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={failureData} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="value">
                  {failureData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#16161f', border: '1px solid #1e1e2e', fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <div className="flex justify-between items-center px-4 py-3 bg-bg-secondary border-b border-bg-border">
          <h3 className="text-sm font-semibold text-text-primary">Results ({resultTotal})</h3>
          <div className="flex gap-2">
            {[
              { label: 'All', value: undefined },
              { label: 'Passed', value: true },
              { label: 'Failed', value: false },
            ].map(({ label, value }) => (
              <button
                key={label}
                onClick={() => { setFilterPassed(value); setResultPage(1) }}
                className={`text-xs px-2 py-1 rounded border ${filterPassed === value ? 'border-accent-blue text-accent-blue' : 'border-bg-border text-text-muted'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-text-muted text-xs bg-bg-secondary border-b border-bg-border">
              <th className="px-4 py-2">Result</th>
              <th className="px-4 py-2">Score</th>
              <th className="px-4 py-2">Similarity</th>
              <th className="px-4 py-2">Keywords</th>
              <th className="px-4 py-2">Latency</th>
              <th className="px-4 py-2">Hallucination</th>
              <th className="px-4 py-2">Reason</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr key={result.id} className="table-row">
                <td className="px-4 py-2"><PassBadge passed={result.passed} /></td>
                <td className="px-4 py-2 font-mono">{result.final_score?.toFixed(3) ?? '—'}</td>
                <td className="px-4 py-2 font-mono">{result.similarity_score?.toFixed(3) ?? '—'}</td>
                <td className="px-4 py-2 font-mono">{result.keyword_coverage?.toFixed(3) ?? '—'}</td>
                <td className="px-4 py-2 font-mono text-accent-cyan">{ms(result.latency_ms)}</td>
                <td className="px-4 py-2">
                  {result.is_hallucination && <AlertTriangle className="w-4 h-4 text-accent-yellow" />}
                </td>
                <td className="px-4 py-2 text-text-muted text-xs">{result.failure_reason ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {resultTotal > 30 && (
          <div className="flex justify-center gap-2 p-3 border-t border-bg-border">
            <button onClick={() => setResultPage(p => Math.max(1, p - 1))} disabled={resultPage === 1} className="btn-secondary text-xs">Prev</button>
            <span className="text-text-muted text-xs py-1">{resultPage}/{Math.ceil(resultTotal / 30)}</span>
            <button onClick={() => setResultPage(p => p + 1)} disabled={resultPage >= Math.ceil(resultTotal / 30)} className="btn-secondary text-xs">Next</button>
          </div>
        )}
      </div>
    </div>
  )
}
