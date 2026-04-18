/** TypeScript interfaces matching backend Pydantic schemas (backend/app/models/schemas.py) */

// --- Report sub-models ---

export interface HotTopic {
  name: string
  description: string
  mentions_count: number
}

export interface UserProblem {
  description: string
  examples: string[]
}

export interface TrendingDiscussion {
  title: string
  description: string
  post_url: string
  activity_score: number
}

// --- Topic models ---

export interface Topic {
  id: number
  pikabu_id: string
  name: string
  subscribers_count: number | null
  url: string
  source?: string
}

export interface TopicListResponse {
  topics: Topic[]
}

// --- Analysis models ---

export interface AnalysisStartRequest {
  topic_id: number
  source?: string
  habr_topic_id?: number
  vcru_topic_id?: number
}

export interface AnalysisStartResponse {
  task_id: string
  status: string
}

export interface AnalysisStatusResponse {
  task_id: string
  status: string
  progress_percent: number
  current_stage: string | null
  total_chunks: number | null
  processed_chunks: number | null
  error_message: string | null
  report_id: number | null
}

// --- Report models ---

export interface Report {
  id: number
  topic_id: number
  hot_topics: HotTopic[]
  user_problems: UserProblem[]
  trending_discussions: TrendingDiscussion[]
  generated_at: string
  sources?: string
}

export interface ReportListResponse {
  reports: Report[]
}
