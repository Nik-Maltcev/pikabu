import axios from 'axios'
import type {
  TopicListResponse,
  AnalysisStartResponse,
  AnalysisStatusResponse,
  ReportListResponse,
  Report,
} from '../types/api'

const baseURL = import.meta.env.VITE_API_URL || '/api'
console.log('[API] baseURL:', baseURL)

const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
})

export async function getTopics(search?: string, source?: string): Promise<TopicListResponse> {
  const params: Record<string, string> = {}
  if (search) params.search = search
  if (source) params.source = source
  const { data } = await api.get<TopicListResponse>('/topics', { params })
  return data
}

export async function startAnalysis(
  topicId: number,
  days: number = 30,
  source?: string,
  habrTopicId?: number,
  vcruTopicId?: number,
): Promise<AnalysisStartResponse> {
  const body: Record<string, unknown> = { topic_id: topicId, days }
  if (source) body.source = source
  if (habrTopicId != null) body.habr_topic_id = habrTopicId
  if (vcruTopicId != null) body.vcru_topic_id = vcruTopicId
  const { data } = await api.post<AnalysisStartResponse>('/analysis/start', body)
  return data
}

export async function getAnalysisStatus(taskId: string): Promise<AnalysisStatusResponse> {
  const { data } = await api.get<AnalysisStatusResponse>(`/analysis/status/${taskId}`)
  return data
}

export async function getReports(topicId: number): Promise<ReportListResponse> {
  const { data } = await api.get<ReportListResponse>(`/reports/${topicId}`)
  return data
}

export async function getReport(topicId: number, reportId: number): Promise<Report> {
  const { data } = await api.get<Report>(`/reports/${topicId}/${reportId}`)
  return data
}
