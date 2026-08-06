import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, RefreshCw, Server, MessageSquare } from 'lucide-react'
import { format } from 'date-fns'
import { createEvalRun, fetchEvalRuns, fetchSuites, fetchAvailableModels } from '../api'
import { StatusBadge, QualityGateBadge } from '../components/ui/Badge'
import { ms, pct } from '../components/ui/Metric'
import type { EvalRunSummary, EvalSuiteSummary } from '../types'
import { usePolling } from '../hooks/usePolling'

export function EvalRuns() {
  const [runs, setRuns] = useState<EvalRunSummary[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [suites, setSuites] = useState<EvalSuiteSummary[]>([])
  const [installedModels, setInstalledModels] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [filterStatus, setFilterStatus] = useState('')

  // Form state
  const [selectedSuite, setSelectedSuite] = useState('')
  const [modelName, setModelName] = useState('phi4')
  const [modelProvider, setModelProvider] = useState('ollama')
  const [targetType, setTargetType] = useState('raw_llm')
  const [endpointUrl, setEndpointUrl] = useState('')
  const [systemPromptOverride, setSystemPromptOverride] = useState('')

  const PAGE_SIZE = 20

  const load = async () => {
    try {
      const r = await fetchEvalRuns({
        page,
        page_size: PAGE_SIZE,
        status: filterStatus || undefined,
      })
      setRuns(r.items)
      setTotal(r.total)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    fetchSuites({ active_only: true }).then((r) => setSuites(r.items))
    fetchAvailableModels().then((m) => setInstalledModels(m.installed))
  }, [page, filterStatus])

  const hasRunning = runs.some((r) => r.status === 'running' || r.status === 'pending')
  usePolling(load, 5000, hasRunning)

  const handleCreate = async () => {
    if (!selectedSuite || !modelName.trim()) return
    setCreating(true)
    try {
      await createEvalRun({
        suite_id: selectedSuite,
        model_name: modelName.trim(),
        model_provider: modelProvider,
        target_type: targetType,
        endpoint_url: endpointUrl.trim() || undefined,
        system_prompt_override: systemPromptOverride.trim() || undefined,
      })
      setShowForm(false)
      load()
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Eval Runs</h1>
          <p className="text-sm text-text-muted">{total} total runs</p>
        </div>
        <div className="flex gap-2">
          <button onClick={load} className="btn-secondary">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button onClick={() => setShowForm(!showForm)} className="btn-primary">
            <Plus className="w-4 h-4" /> New Run
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card border-accent-blue/30 space-y-4">
          <h3 className="text-sm font-semibold text-text-primary">Trigger Evaluation Run</h3>

          {/* Row 1: Suite + Target Type + Provider */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-text-muted mb-1 block">Suite</label>
              <select
                className="input w-full"
                value={selectedSuite}
                onChange={(e) => setSelectedSuite(e.target.value)}
              >
                <option value="">Select suite...</option>
                {suites.map((s) => (
                  <option key={s.id} value={s.id}>{s.name} (v{s.version})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Target Type</label>
              <select
                className="input w-full font-semibold text-accent-cyan"
                value={targetType}
                onChange={(e) => setTargetType(e.target.value)}
              >
                <option value="raw_llm">RAW LLM (Direct Output)</option>
                <option value="rag">RAG Pipeline (Docs + Chroma)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 block">Provider</label>
              <select
                className="input w-full"
                value={modelProvider}
                onChange={(e) => setModelProvider(e.target.value)}
              >
                <option value="ollama">Ollama (local / any compatible)</option>
                <option value="openai_compat">OpenAI-compatible</option>
                <option value="gemini">Gemini</option>
              </select>
            </div>
          </div>

          {/* Row 2: Model name (free-text) + Endpoint URL */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-text-muted mb-1 block">Model Name</label>
              <input
                className="input w-full font-mono"
                placeholder="phi4, llama3.2, qwen2.5, ..."
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
                list="installed-models"
              />
              <datalist id="installed-models">
                {installedModels.map((m) => <option key={m} value={m} />)}
              </datalist>
              {installedModels.length > 0 && (
                <p className="text-xs text-text-muted mt-1">
                  Installed: {installedModels.join(', ')}
                </p>
              )}
            </div>
            <div>
              <label className="text-xs text-text-muted mb-1 flex items-center gap-1">
                <Server className="w-3 h-3" /> Endpoint URL
                <span className="text-text-muted/60">(optional — uses server default if blank)</span>
              </label>
              <input
                className="input w-full font-mono"
                placeholder="http://host.docker.internal:11434"
                value={endpointUrl}
                onChange={(e) => setEndpointUrl(e.target.value)}
              />
            </div>
          </div>

          {/* Row 3: System prompt override */}
          <div>
            <label className="text-xs text-text-muted mb-1 flex items-center gap-1">
              <MessageSquare className="w-3 h-3" /> Purpose / System Prompt Override
              <span className="text-text-muted/60">(optional — describes what this LLM is for)</span>
            </label>
            <textarea
              className="input w-full font-mono text-xs"
              rows={3}
              placeholder="e.g. This assistant is specialised in backend architecture. It must provide concise Node.js + PostgreSQL code snippets..."
              value={systemPromptOverride}
              onChange={(e) => setSystemPromptOverride(e.target.value)}
            />
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={!selectedSuite || !modelName.trim() || creating}
              className="btn-primary"
            >
              {creating ? 'Triggering...' : 'Trigger Run'}
            </button>
            <button onClick={() => setShowForm(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        {['', 'pending', 'running', 'completed', 'failed'].map((s) => (
          <button
            key={s}
            onClick={() => { setFilterStatus(s); setPage(1) }}
            className={`text-xs px-3 py-1 rounded border transition-colors ${filterStatus === s ? 'border-accent-blue text-accent-blue bg-accent-blue/10' : 'border-bg-border text-text-muted hover:border-text-muted'}`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-text-muted animate-pulse">Loading...</div>
      ) : runs.length === 0 ? (
        <div className="card text-center text-text-muted py-12">No evaluation runs found.</div>
      ) : (
        <div className="card p-0 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-text-muted text-xs bg-bg-secondary border-b border-bg-border">
                <th className="px-4 py-3">Model</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Trigger</th>
                <th className="px-4 py-3">Pass Rate</th>
                <th className="px-4 py-3">Hallucination</th>
                <th className="px-4 py-3">P95 Latency</th>
                <th className="px-4 py-3">Gate</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="table-row">
                  <td className="px-4 py-3">
                    <Link to={`/evals/${run.id}`} className="text-accent-blue hover:underline font-mono">
                      {run.model_name}
                    </Link>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
                  <td className="px-4 py-3 text-text-muted text-xs">{run.trigger}</td>
                  <td className="px-4 py-3 font-mono">{pct(run.pass_rate)}</td>
                  <td className="px-4 py-3 font-mono text-accent-red">{pct(run.hallucination_rate)}</td>
                  <td className="px-4 py-3 font-mono text-accent-cyan">{ms(run.p95_latency_ms)}</td>
                  <td className="px-4 py-3"><QualityGateBadge passed={run.quality_gate_passed} /></td>
                  <td className="px-4 py-3 text-text-muted text-xs">
                    {format(new Date(run.created_at), 'MMM d HH:mm')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="flex justify-center gap-2">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="btn-secondary text-xs">Prev</button>
          <span className="text-text-muted text-xs py-2">Page {page} of {Math.ceil(total / PAGE_SIZE)}</span>
          <button onClick={() => setPage(p => p + 1)} disabled={page >= Math.ceil(total / PAGE_SIZE)} className="btn-secondary text-xs">Next</button>
        </div>
      )}
    </div>
  )
}
