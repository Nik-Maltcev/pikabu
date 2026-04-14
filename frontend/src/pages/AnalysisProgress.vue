<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAnalysisStatus } from '../api/client'
import type { AnalysisStatusResponse } from '../types/api'

const route = useRoute()
const router = useRouter()
const taskId = route.params.taskId as string

const status = ref<AnalysisStatusResponse | null>(null)
const error = ref('')
const loading = ref(true)

let pollTimer: ReturnType<typeof setInterval> | null = null

const stageLabel = computed(() => {
  if (!status.value) return ''
  const s = status.value.status
  if (s === 'pending') return 'Ожидание...'
  if (s === 'parsing') return 'Парсинг данных с Pikabu...'
  if (s === 'chunk_analysis') {
    const processed = status.value.processed_chunks ?? 0
    const total = status.value.total_chunks ?? 0
    return `Анализ чанка ${processed} из ${total}...`
  }
  if (s === 'aggregating') return 'Агрегация результатов...'
  if (s === 'completed') return 'Анализ завершён!'
  if (s === 'failed') return 'Ошибка анализа'
  return s
})

const isTerminal = computed(() => {
  if (!status.value) return false
  return status.value.status === 'completed' || status.value.status === 'failed'
})

const isFailed = computed(() => status.value?.status === 'failed')
const isCompleted = computed(() => status.value?.status === 'completed')

async function fetchStatus() {
  try {
    const res = await getAnalysisStatus(taskId)
    status.value = res
    error.value = ''
    if (isTerminal.value) {
      stopPolling()
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось получить статус анализа'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  fetchStatus()
  pollTimer = setInterval(fetchStatus, 2000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function goToReport() {
  if (status.value?.report_id != null) {
    // We need topic_id — extract from status or navigate with what we have
    // The AnalysisStatusResponse doesn't include topic_id directly,
    // but the report route needs it. We'll navigate using a workaround:
    // For now, we use report_id and try to get topic from the task context.
    // Since the API status doesn't return topic_id, we'll store it or use a fallback.
    // The route is /reports/:topicId/:reportId — we need topic_id.
    // Let's check if we can get it from the status response or route query.
    const topicId = route.query.topicId as string
    if (topicId) {
      router.push({ name: 'report', params: { topicId, reportId: String(status.value.report_id) } })
    }
  }
}

function goBack() {
  router.push({ name: 'topics' })
}

onMounted(startPolling)
onUnmounted(stopPolling)
</script>

<template>
  <div class="ap-page">
    <header class="ap-header">
      <h1 class="ap-title">Прогресс анализа</h1>
      <p class="ap-task-id">Task ID: {{ taskId }}</p>
    </header>

    <div class="ap-body">
      <!-- Loading state -->
      <div v-if="loading" class="ap-loading">
        <div class="ap-spinner"></div>
        <span>Загрузка статуса…</span>
      </div>

      <!-- Error fetching status -->
      <div v-else-if="error && !status" class="ap-error" role="alert">
        <p>{{ error }}</p>
        <button class="ap-btn ap-btn--secondary" @click="goBack">Вернуться</button>
      </div>

      <!-- Main progress display -->
      <template v-else-if="status">
        <div class="ap-card">
          <!-- Stage label -->
          <p class="ap-stage" :class="{ 'ap-stage--done': isCompleted, 'ap-stage--fail': isFailed }">
            {{ stageLabel }}
          </p>

          <!-- Progress bar -->
          <div class="ap-progress-wrap">
            <div class="ap-progress-bar">
              <div
                class="ap-progress-fill"
                :class="{ 'ap-progress-fill--fail': isFailed, 'ap-progress-fill--done': isCompleted }"
                :style="{ width: status.progress_percent + '%' }"
              ></div>
            </div>
            <span class="ap-progress-pct">{{ status.progress_percent }}%</span>
          </div>

          <!-- Chunk info -->
          <p v-if="status.total_chunks != null && status.total_chunks > 0" class="ap-chunks">
            Чанков обработано: {{ status.processed_chunks ?? 0 }} / {{ status.total_chunks }}
          </p>

          <!-- Error message from backend -->
          <div v-if="isFailed && status.error_message" class="ap-error" role="alert">
            <p>{{ status.error_message }}</p>
          </div>

          <!-- Polling indicator -->
          <div v-if="!isTerminal" class="ap-polling">
            <div class="ap-spinner ap-spinner--sm"></div>
            <span>Обновление статуса…</span>
          </div>

          <!-- Actions -->
          <div class="ap-actions">
            <button
              v-if="isCompleted && status.report_id != null"
              class="ap-btn"
              @click="goToReport"
            >
              Перейти к отчёту
            </button>
            <button
              v-if="isFailed"
              class="ap-btn ap-btn--secondary"
              @click="goBack"
            >
              Вернуться
            </button>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.ap-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 40px 24px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.ap-header {
  text-align: center;
  margin-bottom: 32px;
}

.ap-title {
  font-size: 32px;
  margin: 0 0 8px;
}

.ap-task-id {
  font-size: 13px;
  color: var(--text);
  font-family: var(--mono);
}

.ap-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* Card */
.ap-card {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  align-items: center;
  text-align: center;
}

/* Stage label */
.ap-stage {
  font-size: 18px;
  font-weight: 500;
  color: var(--text-h);
  margin: 0;
}

.ap-stage--done {
  color: #16a34a;
}

.ap-stage--fail {
  color: #b91c1c;
}

@media (prefers-color-scheme: dark) {
  .ap-stage--done {
    color: #4ade80;
  }
  .ap-stage--fail {
    color: #fca5a5;
  }
}

/* Progress bar */
.ap-progress-wrap {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
}

.ap-progress-bar {
  flex: 1;
  height: 12px;
  background: var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.ap-progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 6px;
  transition: width 0.4s ease;
}

.ap-progress-fill--done {
  background: #16a34a;
}

.ap-progress-fill--fail {
  background: #b91c1c;
}

@media (prefers-color-scheme: dark) {
  .ap-progress-fill--done {
    background: #4ade80;
  }
  .ap-progress-fill--fail {
    background: #fca5a5;
  }
}

.ap-progress-pct {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-h);
  min-width: 40px;
  text-align: right;
  font-family: var(--mono);
}

/* Chunks info */
.ap-chunks {
  font-size: 14px;
  color: var(--text);
  margin: 0;
}

/* Polling indicator */
.ap-polling {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text);
}

/* Actions */
.ap-actions {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

/* Buttons — matching TopicSelector style */
.ap-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-size: 15px;
  font-family: var(--sans);
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.2s;
}

.ap-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.ap-btn--secondary {
  background: transparent;
  color: var(--text-h);
  border: 1px solid var(--border);
}

.ap-btn--secondary:hover {
  background: var(--accent-bg);
}

/* Error */
.ap-error {
  width: 100%;
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
  text-align: left;
}

.ap-error p {
  margin: 0 0 8px;
}

.ap-error p:last-child {
  margin-bottom: 0;
}

@media (prefers-color-scheme: dark) {
  .ap-error {
    background: rgba(185, 28, 28, 0.15);
    color: #fca5a5;
    border-color: rgba(185, 28, 28, 0.3);
  }
}

/* Loading / spinner */
.ap-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: var(--text);
}

.ap-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: ap-spin 0.6s linear infinite;
}

.ap-spinner--sm {
  width: 14px;
  height: 14px;
}

@keyframes ap-spin {
  to { transform: rotate(360deg); }
}
</style>
