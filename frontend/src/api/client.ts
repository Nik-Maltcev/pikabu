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
  contactType?: string,
  contactValue?: string,
  waitOnPage?: boolean,
  authToken?: string,
): Promise<AnalysisStartResponse> {
  const body: Record<string, unknown> = { 
    topic_id: topicId, 
    days,
    contact_type: contactType || '',
    contact_value: contactValue || '',
    wait_on_page: waitOnPage || false,
  }
  if (fingerprint) body.fingerprint = fingerprint
  
  const headers: Record<string, string> = {}
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`
  }
  
  const { data } = await api.post<AnalysisStartResponse>('/analysis/start', body, { headers })
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

export async function createPayment(reportId: number, promoCode?: string): Promise<PaymentCreateResponse> {
  const body: Record<string, unknown> = { report_id: reportId }
  if (promoCode) body.promo_code = promoCode
  const { data } = await api.post<PaymentCreateResponse>('/payment/create', body)
  return data
}

export async function checkPayment(reportId: number, token?: string, topicId?: number): Promise<PaymentCheckResponse> {
  const params: Record<string, string | number> = { report_id: reportId }
  if (token) params.token = token
  if (topicId) params.topic_id = topicId
  const { data } = await api.get<PaymentCheckResponse>('/payment/check', { params })
  return data
}

export async function createPaidAnalysis(topicId: number, days: number, fingerprint: string, promoCode?: string): Promise<PaymentCreateResponse> {
  const body: Record<string, unknown> = { topic_id: topicId, days, fingerprint }
  if (promoCode) body.promo_code = promoCode
  const { data } = await api.post<PaymentCreateResponse>('/payment/create-for-analysis', body)
  return data
}

export interface PromoCheckResponse {
  valid: boolean
  price?: number
  discount_percent?: number
  original_price?: number
}

export async function checkPromoCode(code: string): Promise<PromoCheckResponse> {
  const { data } = await api.post<PromoCheckResponse>('/payment/promo/check', { code })
  return data
}

// --- Auth API ---

export interface AuthResponse {
  success: boolean
  token: string
  user: { id: number; email: string }
}

export interface AuthCheckResponse {
  authenticated: boolean
  user?: { id: number; email: string }
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/register', { email, password })
  return data
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post<AuthResponse>('/auth/login', { email, password })
  return data
}

export async function checkAuth(token: string): Promise<AuthCheckResponse> {
  const { data } = await api.get<AuthCheckResponse>('/auth/check', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}


// --- Chat API ---

export interface ChatResponse {
  answer: string
  questions_remaining: number
}

export async function askQuestion(topicId: number, question: string, accessToken: string): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', {
    topic_id: topicId,
    question,
    access_token: accessToken,
  })
  return data
}
