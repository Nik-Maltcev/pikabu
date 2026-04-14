<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTopics, startAnalysis } from '../api/client'
import type { Topic } from '../types/api'

const router = useRouter()

const topics = ref<Topic[]>([])
const searchQuery = ref('')
const selectedTopic = ref<Topic | null>(null)
const selectedDays = ref(30)
const loading = ref(false)
const analyzing = ref(false)
const error = ref('')

let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function loadTopics(search?: string) {
  loading.value = true
  error.value = ''
  try {
    const res = await getTopics(search || undefined)
    topics.value = res?.topics ?? []
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось загрузить список тем'
  } finally {
    loading.value = false
  }
}

function onSearchInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    loadTopics(searchQuery.value)
  }, 300)
}

function selectTopic(topic: Topic) {
  selectedTopic.value = topic
}

async function onStartAnalysis() {
  if (!selectedTopic.value) return
  analyzing.value = true
  error.value = ''
  try {
    const res = await startAnalysis(selectedTopic.value.id, selectedDays.value)
    router.push({ name: 'analysis', params: { taskId: res.task_id }, query: { topicId: String(selectedTopic.value.id) } })
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось запустить анализ'
  } finally {
    analyzing.value = false
  }
}

function formatSubscribers(count: number | null): string {
  if (count == null) return '—'
  if (count >= 1_000_000) return (count / 1_000_000).toFixed(1) + 'M'
  if (count >= 1_000) return (count / 1_000).toFixed(1) + 'K'
  return String(count)
}

onMounted(() => loadTopics())
</script>

<template>
  <div class="topic-selector">
    <header class="ts-header">
      <h1 class="ts-title">Pikabu Topic Analyzer</h1>
      <p class="ts-subtitle">Выберите тему для анализа контента</p>
    </header>

    <div class="ts-body">
      <div class="ts-search-panel">
        <div class="ts-search-wrap">
          <svg class="ts-search-icon" viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
            <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l4.08 4.08a.75.75 0 11-1.06 1.06l-4.08-4.08A7 7 0 012 9z" clip-rule="evenodd"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            class="ts-search-input"
            placeholder="Поиск по названию темы…"
            @input="onSearchInput"
          />
        </div>

        <div v-if="error" class="ts-error" role="alert">{{ error }}</div>

        <div v-if="loading && topics.length === 0" class="ts-loading">
          <div class="ts-spinner"></div>
          <span>Загрузка тем…</span>
        </div>

        <ul v-else class="ts-list" role="listbox" aria-label="Список тем">
          <li
            v-for="topic in topics"
            :key="topic.id"
            role="option"
            :aria-selected="selectedTopic?.id === topic.id"
            class="ts-item"
            :class="{ 'ts-item--selected': selectedTopic?.id === topic.id }"
            @click="selectTopic(topic)"
          >
            <span class="ts-item-name">{{ topic.name }}</span>
            <span class="ts-item-subs">{{ formatSubscribers(topic.subscribers_count) }}</span>
          </li>
          <li v-if="!loading && topics.length === 0" class="ts-empty">
            Темы не найдены
          </li>
        </ul>
      </div>

      <aside class="ts-details-panel">
        <template v-if="selectedTopic">
          <h2 class="ts-detail-title">{{ selectedTopic.name }}</h2>
          <dl class="ts-detail-meta">
            <dt>Подписчики</dt>
            <dd>{{ selectedTopic.subscribers_count ?? '—' }}</dd>
          </dl>
          <a :href="selectedTopic.url" target="_blank" rel="noopener" class="ts-detail-link">
            Открыть на Pikabu ↗
          </a>
        </template>
        <template v-else>
          <div class="ts-detail-placeholder">
            <p>Выберите тему из списка слева, чтобы увидеть подробности</p>
          </div>
        </template>

        <div class="ts-period">
          <label class="ts-period-label">Период анализа:</label>
          <div class="ts-period-buttons">
            <button
              v-for="d in [7, 14, 30]"
              :key="d"
              class="ts-period-btn"
              :class="{ 'ts-period-btn--active': selectedDays === d }"
              @click="selectedDays = d"
            >
              {{ d }} дней
            </button>
          </div>
        </div>

        <button
          class="ts-btn"
          :disabled="!selectedTopic || analyzing"
          @click="onStartAnalysis"
        >
          <template v-if="analyzing">
            <div class="ts-spinner ts-spinner--sm"></div>
            Запуск…
          </template>
          <template v-else>
            Начать анализ
          </template>
        </button>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.topic-selector {
  max-width: 960px;
  margin: 0 auto;
  padding: 40px 24px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.ts-header {
  text-align: center;
  margin-bottom: 32px;
}

.ts-title {
  font-size: 32px;
  margin: 0 0 8px;
}

.ts-subtitle {
  color: var(--text);
  font-size: 16px;
}

.ts-body {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
  flex: 1;
}

@media (max-width: 768px) {
  .ts-body {
    grid-template-columns: 1fr;
  }
}

/* Search panel */
.ts-search-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.ts-search-wrap {
  position: relative;
  margin-bottom: 12px;
}

.ts-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text);
  pointer-events: none;
}

.ts-search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px 10px 38px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg);
  color: var(--text-h);
  font-size: 15px;
  font-family: var(--sans);
  outline: none;
  transition: border-color 0.2s;
}

.ts-search-input:focus {
  border-color: var(--accent);
}

/* Topic list */
.ts-list {
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
  max-height: 60vh;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.ts-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}

.ts-item:last-child {
  border-bottom: none;
}

.ts-item:hover {
  background: var(--accent-bg);
}

.ts-item--selected {
  background: var(--accent-bg);
  border-left: 3px solid var(--accent);
}

.ts-item-name {
  font-weight: 500;
  color: var(--text-h);
}

.ts-item-subs {
  font-size: 13px;
  color: var(--text);
  white-space: nowrap;
  margin-left: 12px;
}

.ts-empty {
  padding: 24px;
  text-align: center;
  color: var(--text);
}

/* Details panel */
.ts-details-panel {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-self: start;
  position: sticky;
  top: 24px;
}

.ts-detail-title {
  font-size: 20px;
  margin: 0;
}

.ts-detail-meta {
  margin: 0;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  font-size: 14px;
}

.ts-detail-meta dt {
  color: var(--text);
}

.ts-detail-meta dd {
  margin: 0;
  color: var(--text-h);
  font-weight: 500;
}

.ts-detail-link {
  font-size: 14px;
  color: var(--accent);
  text-decoration: none;
}

.ts-detail-link:hover {
  text-decoration: underline;
}

.ts-detail-placeholder {
  color: var(--text);
  font-size: 14px;
  text-align: center;
  padding: 16px 0;
}

/* Button */
.ts-btn {
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
  margin-top: auto;
}

.ts-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.ts-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Error */
.ts-error {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 14px;
  margin-bottom: 12px;
}

@media (prefers-color-scheme: dark) {
  .ts-error {
    background: rgba(185, 28, 28, 0.15);
    color: #fca5a5;
    border-color: rgba(185, 28, 28, 0.3);
  }
}

/* Loading / spinner */
.ts-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: var(--text);
}

.ts-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.ts-spinner--sm {
  width: 14px;
  height: 14px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Period selector */
.ts-period {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ts-period-label {
  font-size: 14px;
  color: var(--text);
}

.ts-period-buttons {
  display: flex;
  gap: 6px;
}

.ts-period-btn {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text-h);
  font-size: 14px;
  font-family: var(--sans);
  cursor: pointer;
  transition: all 0.15s;
}

.ts-period-btn:hover {
  background: var(--accent-bg);
}

.ts-period-btn--active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.ts-period-btn--active:hover {
  opacity: 0.9;
}
</style>
