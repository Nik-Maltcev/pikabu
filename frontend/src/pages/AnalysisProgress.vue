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
  const s = status.value.current_stage
  if (s) return s
  const st = status.value.status
  if (st === 'queued') return 'В очереди...'
  if (st === 'pending') return 'Ожидание запуска...'
  if (st === 'parsing') return 'Сбор данных...'
  if (st === 'chunk_analysis') return 'AI-анализ данных...'
  if (st === 'aggregating') return 'Формирование отчёта...'
  if (st === 'completed') return 'Анализ завершён!'
  if (st === 'failed') return 'Ошибка'
  return st
})

const statusIcon = computed(() => {
  if (!status.value) return '⏳'
  const st = status.value.status
  if (st === 'completed') return '✅'
  if (st === 'failed') return '❌'
  if (st === 'queued') return '🕐'
  if (st === 'parsing') return '📡'
  if (st === 'chunk_analysis') return '🧠'
  if (st === 'aggregating') return '📊'
  return '⏳'
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
    if (isTerminal.value) stopPolling()
  } catch (e: any) {
    if (e?.response?.status === 404) {
      stopPolling()
      router.push({ name: 'topics' })
      return
    }
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось получить статус'
  } finally {
    loading.value = false
  }
}

function startPolling() {
  fetchStatus()
  pollTimer = setInterval(fetchStatus, 2500)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

function goToReport() {
  if (status.value?.report_id != null) {
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
    <div v-if="loading" class="ap-center">
      <div class="ap-spinner-lg"></div>
      <p class="ap-loading-text">Загрузка...</p>
    </div>

    <div v-else-if="error && !status" class="ap-center">
      <p class="ap-error-text">{{ error }}</p>
      <button class="ap-btn ap-btn--outline" @click="goBack">Вернуться</button>
    </div>

    <template v-else-if="status">
      <div class="ap-card">
        <div class="ap-icon">{{ statusIcon }}</div>
        <h1 class="ap-stage" :class="{ 'ap-stage--done': isCompleted, 'ap-stage--fail': isFailed }">
          {{ stageLabel }}
        </h1>

        <div class="ap-progress">
          <div class="ap-bar">
            <div
              class="ap-fill"
              :class="{ 'ap-fill--done': isCompleted, 'ap-fill--fail': isFailed }"
              :style="{ width: status.progress_percent + '%' }"
            ></div>
          </div>
          <span class="ap-pct">{{ status.progress_percent }}%</span>
        </div>

        <p v-if="status.total_chunks && status.total_chunks > 0" class="ap-meta">
          Обработано чанков: {{ status.processed_chunks ?? 0 }} / {{ status.total_chunks }}
        </p>

        <div v-if="!isTerminal" class="ap-pulse">
          <span class="ap-dot"></span>
          <span class="ap-pulse-text">Обновляется автоматически</span>
        </div>

        <div v-if="isFailed && status.error_message" class="ap-error-box">
          {{ status.error_message }}
        </div>

        <div class="ap-actions">
          <button v-if="isCompleted && status.report_id != null" class="ap-btn ap-btn--primary" @click="goToReport">
            📄 Посмотреть отчёт
          </button>
          <button v-if="isFailed" class="ap-btn ap-btn--outline" @click="goBack">
            ← Назад
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ap-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: #f8f9fa;
  font-family: 'Inter', system-ui, sans-serif;
}
.ap-center { text-align: center; }
.ap-card {
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 16px;
  padding: 48px 40px;
  max-width: 500px;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  box-shadow: 0 4px 24px rgba(0,0,0,0.04);
}
.ap-icon { font-size: 48px; }
.ap-stage { font-size: 22px; font-weight: 600; color: #1b1b1d; margin: 0; text-align: center; }
.ap-stage--done { color: #16a34a; }
.ap-stage--fail { color: #dc2626; }
.ap-progress { width: 100%; display: flex; align-items: center; gap: 12px; }
.ap-bar { flex: 1; height: 14px; background: #f0f0f0; border-radius: 7px; overflow: hidden; }
.ap-fill { height: 100%; background: linear-gradient(90deg, #7c3aed, #a855f7); border-radius: 7px; transition: width 0.5s ease; }
.ap-fill--done { background: linear-gradient(90deg, #16a34a, #4ade80); }
.ap-fill--fail { background: linear-gradient(90deg, #dc2626, #f87171); }
.ap-pct { font-size: 18px; font-weight: 700; color: #1b1b1d; min-width: 48px; text-align: right; font-variant-numeric: tabular-nums; }
.ap-meta { font-size: 14px; color: #6b7280; margin: 0; }
.ap-pulse { display: flex; align-items: center; gap: 8px; }
.ap-dot { width: 8px; height: 8px; border-radius: 50%; background: #7c3aed; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.5; transform: scale(1.3); } }
.ap-pulse-text { font-size: 13px; color: #9ca3af; }
.ap-error-box { width: 100%; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 16px; font-size: 14px; color: #dc2626; text-align: left; }
.ap-error-text { color: #dc2626; font-size: 16px; margin: 0 0 16px; }
.ap-actions { display: flex; gap: 12px; margin-top: 8px; }
.ap-btn { display: inline-flex; align-items: center; gap: 8px; padding: 14px 28px; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; font-family: inherit; cursor: pointer; transition: all 0.15s; }
.ap-btn--primary { background: #7c3aed; color: #fff; }
.ap-btn--primary:hover { background: #6d28d9; transform: translateY(-1px); }
.ap-btn--outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.ap-btn--outline:hover { background: #f9fafb; }
.ap-spinner-lg { width: 40px; height: 40px; border: 3px solid #e5e5e5; border-top-color: #7c3aed; border-radius: 50%; animation: spin 0.7s linear infinite; margin: 0 auto 16px; }
.ap-loading-text { color: #6b7280; font-size: 16px; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 540px) { .ap-card { padding: 32px 20px; } .ap-stage { font-size: 18px; } }
</style>
