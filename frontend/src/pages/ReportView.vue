<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReport } from '../api/client'
import type { Report } from '../types/api'

const route = useRoute()
const router = useRouter()

const topicId = Number(route.params.topicId)
const reportId = Number(route.params.reportId)

const report = ref<Report | null>(null)
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

async function loadReport() {
  loading.value = true
  error.value = ''
  try {
    report.value = await getReport(topicId, reportId)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось загрузить отчёт'
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push({ name: 'reports', params: { topicId: String(topicId) } })
}

onMounted(loadReport)
</script>

<template>
  <div class="rv-page">
    <header class="rv-header">
      <h1 class="rv-title">Отчёт по анализу</h1>
      <button class="rv-back" @click="goBack">← Назад к списку отчётов</button>
    </header>

    <!-- Loading -->
    <div v-if="loading" class="rv-loading">
      <div class="rv-spinner"></div>
      <span>Загрузка отчёта…</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="rv-error" role="alert">
      <p>{{ error }}</p>
      <button class="rv-btn rv-btn--secondary" @click="goBack">Вернуться</button>
    </div>

    <!-- Report content -->
    <template v-else-if="report">
      <p class="rv-date">Сгенерирован: {{ formatDate(report.generated_at) }}</p>

      <!-- Section 1: Hot Topics -->
      <section class="rv-section">
        <h2 class="rv-section-title">🔥 Часто обсуждаемые темы</h2>
        <div v-if="report.hot_topics.length === 0" class="rv-empty">Нет данных</div>
        <ul v-else class="rv-list">
          <li v-for="(ht, i) in report.hot_topics" :key="i" class="rv-card">
            <div class="rv-card-header">
              <span class="rv-card-name">{{ ht.name }}</span>
              <span class="rv-badge">{{ ht.mentions_count }} упоминаний</span>
            </div>
            <p class="rv-card-desc">{{ ht.description }}</p>
          </li>
        </ul>
      </section>

      <!-- Section 2: User Problems -->
      <section class="rv-section">
        <h2 class="rv-section-title">⚠️ Проблемы пользователей</h2>
        <div v-if="report.user_problems.length === 0" class="rv-empty">Нет данных</div>
        <ul v-else class="rv-list">
          <li v-for="(up, i) in report.user_problems" :key="i" class="rv-card">
            <p class="rv-card-desc">{{ up.description }}</p>
            <div v-if="up.examples.length > 0" class="rv-examples">
              <span class="rv-examples-label">Примеры:</span>
              <ul class="rv-examples-list">
                <li v-for="(ex, j) in up.examples" :key="j">{{ ex }}</li>
              </ul>
            </div>
          </li>
        </ul>
      </section>

      <!-- Section 3: Trending Discussions -->
      <section class="rv-section">
        <h2 class="rv-section-title">📈 Трендовые дискуссии</h2>
        <div v-if="report.trending_discussions.length === 0" class="rv-empty">Нет данных</div>
        <ul v-else class="rv-list">
          <li v-for="(td, i) in report.trending_discussions" :key="i" class="rv-card">
            <div class="rv-card-header">
              <span class="rv-card-name">{{ td.title }}</span>
              <span class="rv-badge rv-badge--score">Активность: {{ td.activity_score }}</span>
            </div>
            <p class="rv-card-desc">{{ td.description }}</p>
            <a
              :href="td.post_url"
              target="_blank"
              rel="noopener"
              class="rv-link"
            >
              Открыть на Pikabu ↗
            </a>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.rv-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 24px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.rv-header {
  text-align: center;
  margin-bottom: 24px;
}

.rv-title {
  font-size: 32px;
  margin: 0 0 12px;
}

.rv-back {
  background: none;
  border: none;
  color: var(--accent);
  font-size: 14px;
  font-family: var(--sans);
  cursor: pointer;
  padding: 0;
}

.rv-back:hover {
  text-decoration: underline;
}

.rv-date {
  text-align: center;
  font-size: 14px;
  color: var(--text);
  margin: 0 0 28px;
}

/* Sections */
.rv-section {
  margin-bottom: 32px;
}

.rv-section-title {
  font-size: 22px;
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.rv-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rv-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: box-shadow 0.2s;
}

.rv-card:hover {
  box-shadow: var(--shadow);
}

.rv-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.rv-card-name {
  font-weight: 500;
  color: var(--text-h);
  font-size: 16px;
}

.rv-badge {
  font-size: 12px;
  font-family: var(--mono);
  padding: 3px 8px;
  border-radius: 4px;
  color: var(--accent);
  background: var(--accent-bg);
  white-space: nowrap;
}

.rv-badge--score {
  color: #16a34a;
  background: rgba(22, 163, 74, 0.1);
}

@media (prefers-color-scheme: dark) {
  .rv-badge--score {
    color: #4ade80;
    background: rgba(74, 222, 128, 0.15);
  }
}

.rv-card-desc {
  margin: 0;
  font-size: 15px;
  color: var(--text);
  line-height: 1.5;
}

/* Examples */
.rv-examples {
  margin-top: 4px;
}

.rv-examples-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-h);
}

.rv-examples-list {
  margin: 4px 0 0;
  padding-left: 20px;
  font-size: 14px;
  color: var(--text);
  line-height: 1.6;
}

/* Link */
.rv-link {
  font-size: 14px;
  color: var(--accent);
  text-decoration: none;
  align-self: flex-start;
}

.rv-link:hover {
  text-decoration: underline;
}

/* Empty state */
.rv-empty {
  text-align: center;
  color: var(--text);
  font-size: 14px;
  padding: 20px;
  border: 1px dashed var(--border);
  border-radius: 8px;
}

/* Error */
.rv-error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 14px;
  text-align: left;
}

.rv-error p {
  margin: 0 0 8px;
}

@media (prefers-color-scheme: dark) {
  .rv-error {
    background: rgba(185, 28, 28, 0.15);
    color: #fca5a5;
    border-color: rgba(185, 28, 28, 0.3);
  }
}

/* Buttons */
.rv-btn {
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

.rv-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.rv-btn--secondary {
  background: transparent;
  color: var(--text-h);
  border: 1px solid var(--border);
}

.rv-btn--secondary:hover {
  background: var(--accent-bg);
}

/* Loading / spinner */
.rv-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: var(--text);
}

.rv-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: rv-spin 0.6s linear infinite;
}

@keyframes rv-spin {
  to { transform: rotate(360deg); }
}
</style>
