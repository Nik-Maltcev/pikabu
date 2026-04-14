<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReports } from '../api/client'
import type { Report } from '../types/api'

const route = useRoute()
const router = useRouter()
const topicId = Number(route.params.topicId)

const reports = ref<Report[]>([])
const loading = ref(true)
const error = ref('')

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function loadReports() {
  loading.value = true
  error.value = ''
  try {
    const res = await getReports(topicId)
    reports.value = res.reports
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось загрузить список отчётов'
  } finally {
    loading.value = false
  }
}

function openReport(reportId: number) {
  router.push({ name: 'report', params: { topicId: String(topicId), reportId: String(reportId) } })
}

function goBack() {
  router.push({ name: 'topics' })
}

onMounted(loadReports)
</script>

<template>
  <div class="rh-page">
    <header class="rh-header">
      <h1 class="rh-title">История отчётов</h1>
      <button class="rh-back" @click="goBack">← Назад к выбору темы</button>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="rh-loading">
      <div class="rh-spinner"></div>
      <span>Загрузка отчётов…</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rh-error" role="alert">
      <p>{{ error }}</p>
      <button class="rh-btn rh-btn--secondary" @click="goBack">Вернуться</button>
    </div>

    <!-- Empty state -->
    <div v-else-if="reports.length === 0" class="rh-empty">
      <p>Для этой темы пока нет отчётов</p>
      <button class="rh-btn rh-btn--secondary" @click="goBack">Вернуться к выбору темы</button>
    </div>

    <!-- Report list -->
    <ul v-else class="rh-list" role="list" aria-label="Список отчётов">
      <li
        v-for="report in reports"
        :key="report.id"
        class="rh-card"
        role="listitem"
        tabindex="0"
        @click="openReport(report.id)"
        @keydown.enter="openReport(report.id)"
      >
        <div class="rh-card-header">
          <span class="rh-card-date">{{ formatDate(report.generated_at) }}</span>
        </div>
        <div class="rh-card-stats">
          <span class="rh-stat">
            <span class="rh-stat-icon">🔥</span>
            <span class="rh-stat-value">{{ report.hot_topics.length }}</span>
            <span class="rh-stat-label">тем</span>
          </span>
          <span class="rh-stat">
            <span class="rh-stat-icon">⚠️</span>
            <span class="rh-stat-value">{{ report.user_problems.length }}</span>
            <span class="rh-stat-label">проблем</span>
          </span>
          <span class="rh-stat">
            <span class="rh-stat-icon">📈</span>
            <span class="rh-stat-value">{{ report.trending_discussions.length }}</span>
            <span class="rh-stat-label">дискуссий</span>
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.rh-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 24px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.rh-header {
  text-align: center;
  margin-bottom: 24px;
}

.rh-title {
  font-size: 32px;
  margin: 0 0 12px;
}

.rh-back {
  background: none;
  border: none;
  color: var(--accent);
  font-size: 14px;
  font-family: var(--sans);
  cursor: pointer;
  padding: 0;
}

.rh-back:hover {
  text-decoration: underline;
}

/* Report list */
.rh-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rh-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.rh-card:hover {
  box-shadow: var(--shadow);
  border-color: var(--accent-border);
}

.rh-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.rh-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rh-card-date {
  font-weight: 500;
  color: var(--text-h);
  font-size: 16px;
}

/* Stats row */
.rh-card-stats {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.rh-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--text);
}

.rh-stat-icon {
  font-size: 14px;
}

.rh-stat-value {
  font-weight: 500;
  color: var(--text-h);
  font-family: var(--mono);
}

.rh-stat-label {
  color: var(--text);
}

/* Empty state */
.rh-empty {
  text-align: center;
  color: var(--text);
  font-size: 15px;
  padding: 40px 20px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.rh-empty p {
  margin: 0;
}

/* Error */
.rh-error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
  text-align: left;
}

.rh-error p {
  margin: 0 0 8px;
}

@media (prefers-color-scheme: dark) {
  .rh-error {
    background: rgba(185, 28, 28, 0.15);
    color: #fca5a5;
    border-color: rgba(185, 28, 28, 0.3);
  }
}

/* Buttons */
.rh-btn {
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

.rh-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.rh-btn--secondary {
  background: transparent;
  color: var(--text-h);
  border: 1px solid var(--border);
}

.rh-btn--secondary:hover {
  background: var(--accent-bg);
}

/* Loading / spinner */
.rh-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: var(--text);
}

.rh-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: rh-spin 0.6s linear infinite;
}

@keyframes rh-spin {
  to { transform: rotate(360deg); }
}
</style>
