import { apiClient } from './client'
import type {
  AnalyticsSummary,
  EvalResult,
  EvalRun,
  EvalRunSummary,
  EvalSuite,
  EvalSuiteSummary,
  GoldenQuestion,
  HealthStatus,
  ModelComparisonItem,
  PaginatedResponse,
  TrendDataPoint,
} from '../types'

// Health
export const fetchHealth = () =>
  apiClient.get<HealthStatus>('/health').then((r) => r.data)

// Suites
export const fetchSuites = (params?: { page?: number; page_size?: number; active_only?: boolean }) =>
  apiClient.get<PaginatedResponse<EvalSuiteSummary>>('/suites', { params }).then((r) => r.data)

export const fetchSuite = (id: string) =>
  apiClient.get<EvalSuite>(`/suites/${id}`).then((r) => r.data)

export const createSuite = (data: { name: string; description?: string; version?: string; tags?: string }) =>
  apiClient.post<EvalSuite>('/suites', data).then((r) => r.data)

export const updateSuite = (id: string, data: Partial<EvalSuite>) =>
  apiClient.patch<EvalSuite>(`/suites/${id}`, data).then((r) => r.data)

export const deleteSuite = (id: string) =>
  apiClient.delete(`/suites/${id}`)

// Questions
export const fetchQuestions = (suiteId: string, params?: { page?: number; page_size?: number; category?: string }) =>
  apiClient.get<PaginatedResponse<GoldenQuestion>>(`/suites/${suiteId}/questions`, { params }).then((r) => r.data)

export const createQuestion = (suiteId: string, data: Partial<GoldenQuestion>) =>
  apiClient.post<GoldenQuestion>(`/suites/${suiteId}/questions`, data).then((r) => r.data)

export const bulkCreateQuestions = (suiteId: string, questions: Partial<GoldenQuestion>[]) =>
  apiClient.post<GoldenQuestion[]>(`/suites/${suiteId}/questions/bulk`, { questions }).then((r) => r.data)

export const deleteQuestion = (suiteId: string, questionId: string) =>
  apiClient.delete(`/suites/${suiteId}/questions/${questionId}`)

// Eval Runs
export const fetchEvalRuns = (params?: {
  page?: number
  page_size?: number
  suite_id?: string
  model_name?: string
  status?: string
}) =>
  apiClient.get<PaginatedResponse<EvalRunSummary>>('/evals', { params }).then((r) => r.data)

export const fetchEvalRun = (id: string) =>
  apiClient.get<EvalRun>(`/evals/${id}`).then((r) => r.data)

export const createEvalRun = (data: { suite_id: string; model_name: string; model_provider?: string }) =>
  apiClient.post<EvalRun>('/evals', data).then((r) => r.data)

export const fetchRunResults = (
  runId: string,
  params?: { page?: number; page_size?: number; passed?: boolean; is_hallucination?: boolean }
) =>
  apiClient.get<PaginatedResponse<EvalResult>>(`/evals/${runId}/results`, { params }).then((r) => r.data)

// Analytics
export const fetchAnalyticsSummary = () =>
  apiClient.get<AnalyticsSummary>('/analytics/summary').then((r) => r.data)

export const fetchModelComparison = (suiteId?: string) =>
  apiClient
    .get<ModelComparisonItem[]>('/analytics/models', { params: suiteId ? { suite_id: suiteId } : undefined })
    .then((r) => r.data)

export const fetchTrends = (params?: { days?: number; model_name?: string }) =>
  apiClient.get<TrendDataPoint[]>('/analytics/trends', { params }).then((r) => r.data)

export const fetchFailureBreakdown = (runId: string) =>
  apiClient.get<Record<string, number>>(`/analytics/failures/${runId}`).then((r) => r.data)

// Models
export const fetchAvailableModels = () =>
  apiClient.get<{ supported: string[]; installed: string[]; default: string }>('/models').then((r) => r.data)
