export interface EvalSuite {
  id: string
  name: string
  description: string | null
  version: string
  is_active: boolean
  tags: string | null
  question_count: number
  created_at: string
  updated_at: string
}

export interface EvalSuiteSummary {
  id: string
  name: string
  version: string
  is_active: boolean
  question_count: number
  created_at: string
}

export interface GoldenQuestion {
  id: string
  suite_id: string
  question: string
  golden_answer: string
  category: string | null
  difficulty: string
  expected_keywords: string | null
  max_latency_ms: number | null
  weight: number
  order_index: number
  created_at: string
  updated_at: string
}

export interface EvalRun {
  id: string
  suite_id: string
  model_name: string
  model_provider: string
  status: string
  trigger: string
  commit_sha: string | null
  commit_branch: string | null
  commit_message: string | null
  commit_author: string | null
  github_repo: string | null
  celery_task_id: string | null
  error_message: string | null
  endpoint_url: string | null
  system_prompt_override: string | null
  total_questions: number
  passed_count: number
  failed_count: number
  hallucination_count: number
  pass_rate: number | null
  hallucination_rate: number | null
  avg_similarity_score: number | null
  avg_keyword_coverage: number | null
  avg_latency_ms: number | null
  p50_latency_ms: number | null
  p95_latency_ms: number | null
  total_runtime_ms: number | null
  quality_gate_passed: boolean | null
  quality_gate_details: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface EvalRunSummary {
  id: string
  suite_id: string
  model_name: string
  status: string
  trigger: string
  endpoint_url?: string | null
  system_prompt_override?: string | null
  pass_rate: number | null
  hallucination_rate: number | null
  p95_latency_ms: number | null
  quality_gate_passed: boolean | null
  created_at: string
}

export interface EvalResult {
  id: string
  run_id: string
  question_id: string
  model_response: string | null
  latency_ms: number | null
  similarity_score: number | null
  keyword_coverage: number | null
  gemini_score: number | null
  gemini_reasoning: string | null
  final_score: number | null
  passed: boolean
  is_hallucination: boolean
  failure_reason: string | null
  error: string | null
  scoring_metadata: Record<string, unknown> | null
  question?: GoldenQuestion
  created_at: string
  updated_at: string
}

export interface EvalResultSummary {
  id: string
  question_id: string
  passed: boolean
  is_hallucination: boolean
  final_score: number | null
  latency_ms: number | null
  failure_reason: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AnalyticsSummary {
  total_runs: number
  avg_pass_rate: number | null
  avg_hallucination_rate: number | null
  avg_p95_latency_ms: number | null
  models_tested: string[]
}

export interface ModelComparisonItem {
  model_name: string
  run_count: number
  avg_pass_rate: number | null
  avg_hallucination_rate: number | null
  avg_p95_latency_ms: number | null
  avg_latency_ms: number | null
  latest_run_id: string | null
}

export interface TrendDataPoint {
  date: string
  pass_rate: number | null
  hallucination_rate: number | null
  p95_latency_ms: number | null
  run_count: number
}

export interface HealthStatus {
  status: string
  version: string
  services: Record<string, string>
}
