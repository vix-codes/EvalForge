import { useEffect, useState } from 'react'
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react'
import { createSuite, deleteSuite, fetchSuites, fetchQuestions, createQuestion, bulkCreateQuestions } from '../api'
import type { EvalSuiteSummary, GoldenQuestion } from '../types'

export function Datasets() {
  const [suites, setSuites] = useState<EvalSuiteSummary[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [questions, setQuestions] = useState<Record<string, GoldenQuestion[]>>({})
  const [loading, setLoading] = useState(true)
  const [showCreateSuite, setShowCreateSuite] = useState(false)
  const [newSuiteName, setNewSuiteName] = useState('')
  const [newSuiteDesc, setNewSuiteDesc] = useState('')
  const [showAddQ, setShowAddQ] = useState<string | null>(null)
  const [newQ, setNewQ] = useState({ question: '', golden_answer: '', category: '', difficulty: 'medium', expected_keywords: '' })

  const load = () => fetchSuites({ page_size: 100 }).then((r) => {
    setSuites(r.items)
    setLoading(false)
  })

  useEffect(() => { load() }, [])

  const toggleExpand = async (id: string) => {
    if (expanded === id) { setExpanded(null); return }
    setExpanded(id)
    if (!questions[id]) {
      const qs = await fetchQuestions(id, { page_size: 100 })
      setQuestions((prev) => ({ ...prev, [id]: qs.items }))
    }
  }

  const handleCreateSuite = async () => {
    if (!newSuiteName.trim()) return
    await createSuite({ name: newSuiteName, description: newSuiteDesc || undefined })
    setShowCreateSuite(false)
    setNewSuiteName('')
    setNewSuiteDesc('')
    load()
  }

  const handleDeleteSuite = async (id: string) => {
    if (!confirm('Delete this suite and all its questions?')) return
    await deleteSuite(id)
    load()
  }

  const handleAddQuestion = async (suiteId: string) => {
    if (!newQ.question.trim() || !newQ.golden_answer.trim()) return
    await createQuestion(suiteId, {
      ...newQ,
      expected_keywords: newQ.expected_keywords || undefined,
      category: newQ.category || undefined,
    })
    setShowAddQ(null)
    setNewQ({ question: '', golden_answer: '', category: '', difficulty: 'medium', expected_keywords: '' })
    const qs = await fetchQuestions(suiteId, { page_size: 100 })
    setQuestions((prev) => ({ ...prev, [suiteId]: qs.items }))
    load()
  }

  if (loading) return <div className="text-text-muted animate-pulse">Loading...</div>

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold text-text-primary">Datasets</h1>
          <p className="text-sm text-text-muted">Manage eval suites and golden questions</p>
        </div>
        <button onClick={() => setShowCreateSuite(!showCreateSuite)} className="btn-primary">
          <Plus className="w-4 h-4" /> New Suite
        </button>
      </div>

      {showCreateSuite && (
        <div className="card border-accent-blue/30 space-y-3">
          <h3 className="text-sm font-semibold text-text-primary">Create Eval Suite</h3>
          <input
            className="input w-full"
            placeholder="Suite name"
            value={newSuiteName}
            onChange={(e) => setNewSuiteName(e.target.value)}
          />
          <input
            className="input w-full"
            placeholder="Description (optional)"
            value={newSuiteDesc}
            onChange={(e) => setNewSuiteDesc(e.target.value)}
          />
          <div className="flex gap-2">
            <button onClick={handleCreateSuite} className="btn-primary">Create</button>
            <button onClick={() => setShowCreateSuite(false)} className="btn-secondary">Cancel</button>
          </div>
        </div>
      )}

      {suites.length === 0 ? (
        <div className="card text-center text-text-muted py-12">
          No suites yet. Create one to get started.
        </div>
      ) : (
        <div className="space-y-2">
          {suites.map((suite) => (
            <div key={suite.id} className="card p-0 overflow-hidden">
              <div
                className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-bg-secondary/50"
                onClick={() => toggleExpand(suite.id)}
              >
                <div className="flex items-center gap-2">
                  {expanded === suite.id ? <ChevronDown className="w-4 h-4 text-text-muted" /> : <ChevronRight className="w-4 h-4 text-text-muted" />}
                  <span className="font-medium text-text-primary">{suite.name}</span>
                  <span className="badge badge-gray">v{suite.version}</span>
                  <span className="text-xs text-text-muted">{suite.question_count} questions</span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteSuite(suite.id) }}
                  className="text-text-muted hover:text-accent-red transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {expanded === suite.id && (
                <div className="border-t border-bg-border">
                  {questions[suite.id]?.length > 0 ? (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-text-muted text-xs bg-bg-secondary border-b border-bg-border">
                          <th className="px-4 py-2">Question</th>
                          <th className="px-4 py-2">Category</th>
                          <th className="px-4 py-2">Difficulty</th>
                          <th className="px-4 py-2">Keywords</th>
                        </tr>
                      </thead>
                      <tbody>
                        {questions[suite.id].map((q) => (
                          <tr key={q.id} className="table-row">
                            <td className="px-4 py-2 max-w-xs truncate" title={q.question}>{q.question}</td>
                            <td className="px-4 py-2 text-text-muted text-xs">{q.category ?? '—'}</td>
                            <td className="px-4 py-2">
                              <span className={`badge ${q.difficulty === 'hard' ? 'badge-red' : q.difficulty === 'easy' ? 'badge-green' : 'badge-yellow'}`}>
                                {q.difficulty}
                              </span>
                            </td>
                            <td className="px-4 py-2 text-text-muted text-xs truncate max-w-xs">{q.expected_keywords ?? '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p className="px-4 py-3 text-text-muted text-sm">No questions in this suite.</p>
                  )}

                  <div className="px-4 py-3 border-t border-bg-border">
                    {showAddQ === suite.id ? (
                      <div className="space-y-2">
                        <textarea className="input w-full h-16 resize-none" placeholder="Question" value={newQ.question} onChange={(e) => setNewQ({ ...newQ, question: e.target.value })} />
                        <textarea className="input w-full h-16 resize-none" placeholder="Golden answer" value={newQ.golden_answer} onChange={(e) => setNewQ({ ...newQ, golden_answer: e.target.value })} />
                        <div className="grid grid-cols-3 gap-2">
                          <input className="input" placeholder="Category" value={newQ.category} onChange={(e) => setNewQ({ ...newQ, category: e.target.value })} />
                          <select className="input" value={newQ.difficulty} onChange={(e) => setNewQ({ ...newQ, difficulty: e.target.value })}>
                            <option value="easy">Easy</option>
                            <option value="medium">Medium</option>
                            <option value="hard">Hard</option>
                          </select>
                          <input className="input" placeholder="Keywords (comma-sep)" value={newQ.expected_keywords} onChange={(e) => setNewQ({ ...newQ, expected_keywords: e.target.value })} />
                        </div>
                        <div className="flex gap-2">
                          <button onClick={() => handleAddQuestion(suite.id)} className="btn-primary text-xs">Add Question</button>
                          <button onClick={() => setShowAddQ(null)} className="btn-secondary text-xs">Cancel</button>
                        </div>
                      </div>
                    ) : (
                      <button onClick={() => setShowAddQ(suite.id)} className="btn-secondary text-xs">
                        <Plus className="w-3 h-3" /> Add Question
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
