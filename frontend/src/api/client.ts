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

export async function getTopics(search?: string): Promise<TopicListResponse> {
  const params: Record<string, string> = {}
  if (search) params.search = search
  const { data } = await api.get<TopicListResponse>('/topics', { params })
  return data
}

export async function startAnalysis(
  topicId: number,
  days: number = 30,
  fingerprint?: string,
): Promise<AnalysisStartResponse> {
  const body: Record<string, unknown> = { topic_id: topicId, days }
  if (fingerprint) body.fingerprint = fingerprint
  const { data } = await api.post<AnalysisStartResponse>('/analysis/start', body)
  return data
}

export interface LimitCheckResponse {
  used: number
  remaining: number
  limit: number
}

export async function checkLimit(fingerprint: string): Promise<LimitCheckResponse> {
  const { data } = await api.get<LimitCheckResponse>('/limit/check', {
    params: { fingerprint },
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

// --- Payment API ---

export interface PaymentCreateResponse {
  payment_url: string
  access_token: string
}

export interface PaymentCheckResponse {
  paid: boolean
  access_token?: string
}

export async function createPayment(reportId: number): Promise<PaymentCreateResponse> {
  const { data } = await api.post<PaymentCreateResponse>('/payment/create', { report_id: reportId })
  return data
}

export async function checkPayment(reportId: number, token?: string): Promise<PaymentCheckResponse> {
  const params: Record<string, string | number> = { report_id: reportId }
  if (token) params.token = token
  const { data } = await api.get<PaymentCheckResponse>('/payment/check', { params })
  return data
}
