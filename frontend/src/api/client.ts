import axios from 'axios'
import type {
  TopicListResponse,
  AnalysisStartResponse,
  AnalysisStatusResponse,
  ReportListResponse,
  Report,
} from '../types/api'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export async function getTopics(search?: string): Promise<TopicListResponse> {
  const params = search ? { search } : {}
  const { data } = await api.get<TopicListResponse>('/topics', { params })
  return data
}

export async function startAnalysis(topicId: number): Promise<AnalysisStartResponse> {
  const { data } = await api.post<AnalysisStartResponse>('/analysis/start', {
    topic_id: topicId,
  })
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
