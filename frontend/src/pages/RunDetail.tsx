import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle2, XCircle, AlertTriangle,
  Clock, Activity, ShieldCheck, ShieldX, Cpu, Server
} from 'lucide-react'
import { format } from 'date-fns'
import { fetchEvalRun, fetchRunResults, fetchFailureBreakdown } from '../api'
import { MetricCard, ScoreBar, ms, pct } from '../components/ui/Metric'
import { StatusBadge, QualityGateBadge } from '../components/ui/Badge'
import type { EvalRun, EvalResult } from '../types'
import { usePolling } from '../hooks/usePolling'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const PIE_COLORS = ['#ef4444', '#f59e0b', '#6366f1', '#64748b']

const CHART_STYLE = {
  background: '#0d0d1a',
  border: '1px solid rgba(255,255,255,0.06)',
  borderRadius: 8,
  fontSize: 11,
  color: '#94a3b8',
}

function PassBadge({ passed }: { passed: boolean | null | undefined }) {
  if (passed === null || passed === undefined) return <span className="badge-gray">—</span>
  return passed
    ? <span className="badge-green"><CheckCircle2 className="w-3 h-3" /> Pass</span>
    : <span className="badge-red"><XCircle className="w-3 h-3" /> Fail</span>
}

export function RunDetail() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<EvalRun | null>(null)
  const [results, setResults] = useState<EvalResult[]>([])
  const [failures, setFailures] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [resultPage, setResultPage] = useState(1)
  const [resultTotal, setResultTotal] = useState(0)
  const [filterPassed, setFilterPassed] = useState<boolean | undefined>(undefined)
  const [expanded, setExpanded] = useState<string | null>(null)

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
        const fb = await fetchFailureBreakdown(id).catch(() => ({}))
        setFailures(fb)
      }
    } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [id, resultPage, filterPassed])
  usePolling(load, 3000, run?.status === 'running' || run?.status === 'pending')

  if (loading) return (
    <div className="space-y-4 animate-fade-in">
      <div className="skeleton h-16 rounded-xl" />
      <div className="grid grid-cols-4 gap-4">{[...Array(4)].map((_, i) => <div key={i} className="skeleton h-24 rounded-xl" />)}</div>
      <div className="skeleton h-64 rounded-xl" />
    </div>
  )

  if (!run) return (
    <div className="card border-red-500/20 text-red-400 flex items-center gap-2">
      <AlertTriangle className="w-4 h-4" /> Run not found
    </div>
  )

  const isLive = run.status === 'running' || run.status === 'pending'
  const failureData = Object.entries(failures).map(([k, v]) => ({ name: k, value: v }))
  const passRatePct = (run.pass_rate ?? 0) * 100
  const PAGE_SIZE = 30

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Header */}
      <div className="flex items-start gap-4">
        <Link to="/evals" className="mt-1 text-slate-600 hover:text-slate-300 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-white font-mono">{run.model_name}</h1>
            <StatusBadge status={run.status} />
            <QualityGateBadge passed={run.quality_gate_passed} />
            {isLive && <span className="pulse-dot" />}
          </div>
          <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500 flex-wrap">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{format(new Date(run.created_at), 'PPpp')}</span>
            <span className="flex items-center gap-1"><Activity className="w-3 h-3" />trigger: {run.trigger}</span>
            {run.model_provider && <span className="flex items-center gap-1"><Cpu className="w-3 h-3" />{run.model_provider}</span>}
            {run.endpoint_url && <span className="flex items-center gap-1 font-mono"><Server className="w-3 h-3" />{run.endpoint_url}</span>}
            {run.commit_sha && <span className="font-mono">{run.commit_sha.slice(0, 8)}</span>}
          </div>
        </div>
      </div>

      {/* Error banner */}
      {run.error_message && (
        <div className="card border border-red-500/20 bg-red-500/5 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
          <p className="text-red-300 text-sm font-mono">{run.error_message}</p>
        </div>
      )}

      {/* Metrics row 1 */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          label="Pass Rate"
          value={pct(run.pass_rate)}
          icon={<ShieldCheck className="w-4 h-4" />}
          color={(run.pass_rate ?? 0) >= 0.8 ? 'text-emerald-400' : 'text-amber-400'}
          glow={(run.pass_rate ?? 0) >= 0.8}
        />
        <MetricCard
          label="Hallucination"
          value={pct(run.hallucination_rate)}
          icon={<AlertTriangle className="w-4 h-4" />}
          color={(run.hallucination_rate ?? 0) === 0 ? 'text-emerald-400' : 'text-red-400'}
        />
        <MetricCard
          label="P95 Latency"
          value={ms(run.p95_latency_ms)}
          icon={<Clock className="w-4 h-4" />}
          color="text-cyan-400"
        />
        <MetricCard
          label="Avg Latency"
          value={ms(run.avg_latency_ms)}
          color="text-slate-300"
        />
      </div>

      {/* Metrics row 2 */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard label="Total Questions" value={run.total_questions} />
        <MetricCard label="Passed" value={run.passed_count} color="text-emerald-400" />
        <MetricCard label="Failed" value={run.failed_count} color="text-red-400" />
        <MetricCard label="Hallucinations" value={run.hallucination_count} color="text-amber-400" />
      </div>

      {/* Progress + failure breakdown */}
      <div className="grid grid-cols-3 gap-4">
        <div className="card col-span-2 space-y-4">
          <h3 className="text-sm font-semibold text-white">Score Breakdown</h3>
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-2">
              <span>Pass Rate</span><span className="font-mono text-white">{pct(run.pass_rate)}</span>
            </div>
            <ScoreBar value={run.pass_rate ?? 0} color="bg-indigo-500" />
          </div>
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-2">
              <span>Avg Similarity</span><span className="font-mono text-white">{run.avg_similarity_score?.toFixed(3) ?? '—'}</span>
            </div>
            <ScoreBar value={run.avg_similarity_score ?? 0} color="bg-violet-500" />
          </div>
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-2">
              <span>Avg Keyword Coverage</span><span className="font-mono text-white">{run.avg_keyword_coverage?.toFixed(3) ?? '—'}</span>
            </div>
            <ScoreBar value={run.avg_keyword_coverage ?? 0} color="bg-cyan-500" />
          </div>
          {/* Quality gate details */}
          {run.quality_gate_details && (
            <div className="mt-2 pt-4 border-t border-white/5">
              <div className="text-xs text-slate-500 mb-2 uppercase tracking-wider">Quality Gate</div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: 'Pass Rate', ok: run.quality_gate_details.pass_rate_ok },
                  { label: 'Hallucination', ok: run.quality_gate_details.hallucination_rate_ok },
                  { label: 'Latency', ok: run.quality_gate_details.latency_ok },
                ].map(({ label, ok }) => (
                  <div key={label} className={`flex items-center gap-1.5 text-xs rounded-lg px-3 py-2 ${ok ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                    {ok ? <ShieldCheck className="w-3 h-3" /> : <ShieldX className="w-3 h-3" />}
                    {label}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {failureData.length > 0 ? (
          <div className="card">
            <h3 className="text-sm font-semibold text-white mb-3">Failure Reasons</h3>
            <ResponsiveContainer width="100%" height={130}>
              <PieChart>
                <Pie data={failureData} cx="50%" cy="50%" innerRadius={35} outerRadius={58} dataKey="value" paddingAngle={3}>
                  {failureData.map((_, i) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={CHART_STYLE} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1.5 mt-2">
              {failureData.map(({ name, value }, i) => (
                <div key={name} className="flex justify-between text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                    <span className="text-slate-400 font-mono">{name}</span>
                  </span>
                  <span className="text-slate-300 font-mono">{value}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="card flex items-center justify-center text-slate-600">
            <div className="text-center">
              <ShieldCheck className="w-8 h-8 mx-auto mb-2 text-emerald-800" />
              <p className="text-xs">No failures</p>
            </div>
          </div>
        )}
      </div>

      {/* Results table */}
      <div className="card p-0 overflow-hidden">
        <div className="flex justify-between items-center px-5 py-4 border-b border-white/5">
          <h3 className="text-sm font-semibold text-white">
            Question Results
            <span className="ml-2 text-slate-500 font-normal text-xs">({resultTotal} total)</span>
          </h3>
          <div className="flex gap-1.5">
            {[{ label: 'All', value: undefined }, { label: 'Passed', value: true }, { label: 'Failed', value: false }].map(({ label, value }) => (
              <button
                key={label}
                onClick={() => { setFilterPassed(value); setResultPage(1) }}
                className={`text-xs px-3 py-1 rounded-lg border transition-all ${filterPassed === value ? 'border-indigo-500/50 text-indigo-400 bg-indigo-500/10' : 'border-white/10 text-slate-500 hover:text-slate-300'}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-600 uppercase tracking-wider bg-white/[0.02] border-b border-white/5">
              <th className="px-5 py-3">Result</th>
              <th className="px-5 py-3">Final Score</th>
              <th className="px-5 py-3">Similarity</th>
              <th className="px-5 py-3">Keywords</th>
              <th className="px-5 py-3">Gemini</th>
              <th className="px-5 py-3">Latency</th>
              <th className="px-5 py-3">Reason</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <>
                <tr
                  key={result.id}
                  className="table-row cursor-pointer"
                  onClick={() => setExpanded(expanded === result.id ? null : result.id)}
                >
                  <td className="px-5 py-3"><PassBadge passed={result.passed} /></td>
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-white">{result.final_score?.toFixed(3) ?? '—'}</span>
                      {result.final_score != null && (
                        <div className="w-16 progress-bar">
                          <div className={`progress-fill ${result.passed ? 'bg-emerald-500' : 'bg-red-500'}`}
                            style={{ width: `${(result.final_score ?? 0) * 100}%` }} />
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-300">{result.similarity_score?.toFixed(3) ?? '—'}</td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-300">{result.keyword_coverage?.toFixed(3) ?? '—'}</td>
                  <td className="px-5 py-3 font-mono text-xs text-violet-400">{result.gemini_score?.toFixed(2) ?? '—'}</td>
                  <td className="px-5 py-3 font-mono text-xs text-cyan-400">{ms(result.latency_ms)}</td>
                  <td className="px-5 py-3">
                    {result.failure_reason
                      ? <span className="badge-red text-[10px]">{result.failure_reason}</span>
                      : <span className="badge-green text-[10px]">ok</span>
                    }
                  </td>
                </tr>
                {expanded === result.id && (
                  <tr key={`${result.id}-exp`} className="bg-white/[0.02]">
                    <td colSpan={7} className="px-5 py-4 border-b border-white/5">
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        {result.model_response && (
                          <div>
                            <div className="text-slate-500 uppercase tracking-wider mb-1.5">Model Response</div>
                            <pre className="text-slate-300 font-mono text-[11px] whitespace-pre-wrap bg-white/5 rounded-lg p-3 max-h-40 overflow-auto">{result.model_response}</pre>
                          </div>
                        )}
                        {result.gemini_reasoning && (
                          <div>
                            <div className="text-slate-500 uppercase tracking-wider mb-1.5">Gemini Reasoning</div>
                            <p className="text-violet-300 text-[11px] bg-violet-500/5 rounded-lg p-3">{result.gemini_reasoning}</p>
                          </div>
                        )}
                        {result.error && (
                          <div className="col-span-2">
                            <div className="text-red-400 uppercase tracking-wider mb-1.5">Error</div>
                            <pre className="text-red-300 font-mono text-[11px] whitespace-pre-wrap bg-red-500/5 rounded-lg p-3">{result.error}</pre>
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>

        {resultTotal > PAGE_SIZE && (
          <div className="flex justify-center gap-2 p-4 border-t border-white/5">
            <button onClick={() => setResultPage(p => Math.max(1, p - 1))} disabled={resultPage === 1} className="btn-secondary text-xs">Prev</button>
            <span className="text-slate-500 text-xs py-2">{resultPage} / {Math.ceil(resultTotal / PAGE_SIZE)}</span>
            <button onClick={() => setResultPage(p => p + 1)} disabled={resultPage >= Math.ceil(resultTotal / PAGE_SIZE)} className="btn-secondary text-xs">Next</button>
          </div>
        )}
      </div>
    </div>
  )
}
