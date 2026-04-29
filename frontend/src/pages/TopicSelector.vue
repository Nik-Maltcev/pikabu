<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getTopics, startAnalysis, checkLimit } from '../api/client'
import { generateFingerprint } from '../utils/fingerprint'
import type { Topic } from '../types/api'

const router = useRouter()

const allTopics = ref<Topic[]>([])
const searchQuery = ref('')
const selectedTopic = ref<Topic | null>(null)
const selectedDays = ref(14)
const loading = ref(false)
const analyzing = ref(false)
const error = ref('')
const showAllCategories = ref(false)

// Rate limiting
const fingerprint = ref('')
const remainingAnalyses = ref(3)
const limitReached = ref(false)

// Recommended tags
const recommendedTags = ['Маркетинг', 'IT', 'Бизнес', 'AI']

// Main categories with icons
const mainCategories = [
  { icon: '🛒', name: 'Маркетплейсы', desc: 'E-commerce, интернет-магазины' },
  { icon: '💻', name: 'IT', desc: 'Разработка, SaaS, облачные сервисы' },
  { icon: '🏠', name: 'Сервис', desc: 'Услуги для бизнеса и людей' },
  { icon: '🏭', name: 'Бизнес', desc: 'Предпринимательство, стартапы' },
  { icon: '🍽️', name: 'Еда', desc: 'Доставка, рестораны, HoReCa' },
  { icon: '💊', name: 'Здоровье', desc: 'Медицина, wellness, фитнес' },
  { icon: '🏘️', name: 'Инвестиции', desc: 'Финансы, недвижимость' },
]

const filteredTopics = computed(() => {
  if (!searchQuery.value) return allTopics.value
  const q = searchQuery.value.toLowerCase()
  return allTopics.value.filter(t => t.name.toLowerCase().includes(q))
})

async function loadTopics(search?: string) {
  loading.value = true
  error.value = ''
  try {
    const res = await getTopics(search || undefined)
    allTopics.value = res?.topics ?? []
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось загрузить категории'
  } finally {
    loading.value = false
  }
}

function selectByName(name: string) {
  const topic = allTopics.value.find(t => t.name.toLowerCase() === name.toLowerCase())
  if (topic) {
    selectedTopic.value = topic
  } else {
    searchQuery.value = name
    showAllCategories.value = true
  }
}

function selectTopic(topic: Topic) {
  selectedTopic.value = topic
  showAllCategories.value = false
}

const canStartAnalysis = computed(() => {
  return selectedTopic.value !== null && !limitReached.value
})

async function onStartAnalysis() {
  if (!canStartAnalysis.value) return
  analyzing.value = true
  error.value = ''
  try {
    const topicId = selectedTopic.value!.id
    const res = await startAnalysis(topicId, selectedDays.value, fingerprint.value)
    remainingAnalyses.value = Math.max(0, remainingAnalyses.value - 1)
    if (remainingAnalyses.value <= 0) limitReached.value = true
    router.push({
      name: 'analysis',
      params: { taskId: res.task_id },
      query: { topicId: String(topicId) },
    })
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || 'Не удалось запустить анализ'
    if (e?.response?.status === 429) {
      limitReached.value = true
      remainingAnalyses.value = 0
    }
    error.value = detail
  } finally {
    analyzing.value = false
  }
}

onMounted(async () => {
  fingerprint.value = await generateFingerprint()
  try {
    const limit = await checkLimit(fingerprint.value)
    remainingAnalyses.value = limit.remaining
    limitReached.value = limit.remaining <= 0
  } catch {}
  loadTopics()
})
</script>

<template>
  <div class="page">
    <!-- Navbar -->
    <nav class="navbar">
      <div class="nav-container">
        <span class="nav-brand">NicheFind AI</span>
        <div class="nav-links">
          <a class="nav-link nav-link--active">Поиск ниш</a>
        </div>
      </div>
    </nav>

    <!-- Main content -->
    <main class="main">
      <div class="card">
        <h1 class="card-title">Выберите категорию бизнеса</h1>
        <p class="card-desc">Укажите сферу, чтобы ИИ смог подобрать наиболее релевантные данные и тренды.</p>

        <!-- Search -->
        <div class="search-wrap">
          <svg class="search-icon" viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
            <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.45 4.39l4.08 4.08a.75.75 0 11-1.06 1.06l-4.08-4.08A7 7 0 012 9z" clip-rule="evenodd"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="Поиск категорий (например, Кофейня, SaaS...)"
            @focus="showAllCategories = true"
          />
        </div>

        <!-- Recommended tags -->
        <div class="tags-row">
          <span class="tags-label">✨ ИИ РЕКОМЕНДУЕТ:</span>
          <button
            v-for="tag in recommendedTags"
            :key="tag"
            class="tag-chip"
            :class="{ 'tag-chip--active': selectedTopic?.name === tag }"
            @click="selectByName(tag)"
          >{{ tag }}</button>
        </div>

        <!-- Category cards grid -->
        <div v-if="!showAllCategories" class="categories-grid">
          <button
            v-for="cat in mainCategories"
            :key="cat.name"
            class="cat-card"
            :class="{ 'cat-card--selected': selectedTopic?.name === cat.name }"
            @click="selectByName(cat.name)"
          >
            <div class="cat-icon">{{ cat.icon }}</div>
            <div class="cat-info">
              <span class="cat-name">{{ cat.name }}</span>
              <span class="cat-desc">{{ cat.desc }}</span>
            </div>
          </button>
          <button class="cat-card cat-card--all" @click="showAllCategories = true">
            <div class="cat-icon">📋</div>
            <div class="cat-info">
              <span class="cat-name">Все категории</span>
              <span class="cat-desc">Показать полный список</span>
            </div>
          </button>
        </div>

        <!-- Full list (shown on search or "all") -->
        <div v-if="showAllCategories" class="full-list">
          <div v-if="loading" class="list-loading">
            <div class="spinner"></div>
            <span>Загрузка…</span>
          </div>
          <ul v-else class="topic-list">
            <li
              v-for="topic in filteredTopics"
              :key="topic.id"
              class="topic-item"
              :class="{ 'topic-item--selected': selectedTopic?.id === topic.id }"
              @click="selectTopic(topic)"
            >
              <span class="topic-name">{{ topic.name }}</span>
            </li>
            <li v-if="filteredTopics.length === 0" class="topic-empty">
              Категории не найдены
            </li>
          </ul>
          <button class="back-btn" @click="showAllCategories = false">← Назад к основным</button>
        </div>

        <!-- Selected + Period + Action -->
        <div v-if="selectedTopic" class="selection-bar">
          <div class="selection-info">
            <span class="selection-label">Выбрано:</span>
            <span class="selection-name">{{ selectedTopic.name }}</span>
          </div>

          <div class="period-toggle">
            <button
              class="period-btn"
              :class="{ 'period-btn--active': selectedDays === 14 }"
              @click="selectedDays = 14"
            >14 дней</button>
            <button
              class="period-btn period-btn--paid"
              :class="{ 'period-btn--active': selectedDays === 30 }"
              @click="selectedDays = 30"
            >30 дней <span class="paid-badge">₽</span></button>
          </div>
        </div>

        <!-- Error -->
        <div v-if="error" class="error-msg">{{ error }}</div>

        <!-- Limit -->
        <div v-if="limitReached" class="limit-block">
          🔒 Лимит бесплатных анализов исчерпан. Оплатите для продолжения.
        </div>

        <!-- Action button -->
        <div class="action-row">
          <div v-if="!limitReached" class="remaining">
            Бесплатных анализов: <strong>{{ remainingAnalyses }}</strong>
          </div>
          <button
            class="start-btn"
            :disabled="!canStartAnalysis || analyzing"
            @click="onStartAnalysis"
          >
            <template v-if="analyzing">
              <div class="spinner spinner--sm"></div>
              Анализируем…
            </template>
            <template v-else>
              Далее →
            </template>
          </button>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-container">
        <span class="footer-copy">© 2025 NicheFind AI. Профессиональная аналитика бизнес-ниш.</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
}

/* Navbar */
.navbar {
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
}

.nav-container {
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 32px;
}

.nav-brand {
  font-size: 18px;
  font-weight: 700;
  color: #111;
  letter-spacing: -0.5px;
}

.nav-links {
  display: flex;
  gap: 24px;
}

.nav-link {
  font-size: 14px;
  color: #666;
  text-decoration: none;
  cursor: pointer;
}

.nav-link--active {
  color: #00bfa5;
  font-weight: 500;
}

/* Main */
.main {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 48px 24px;
}

.card {
  background: #fff;
  border-radius: 16px;
  padding: 48px;
  max-width: 900px;
  width: 100%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.card-title {
  font-size: 28px;
  font-weight: 700;
  color: #111;
  margin: 0 0 8px;
}

.card-desc {
  font-size: 15px;
  color: #666;
  margin: 0 0 28px;
}

/* Search */
.search-wrap {
  position: relative;
  margin-bottom: 16px;
}

.search-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
}

.search-input {
  width: 100%;
  box-sizing: border-box;
  padding: 14px 16px 14px 44px;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  font-size: 15px;
  font-family: inherit;
  color: #111;
  background: #fafafa;
  outline: none;
  transition: border-color 0.2s, background 0.2s;
}

.search-input:focus {
  border-color: #00bfa5;
  background: #fff;
}

.search-input::placeholder {
  color: #aaa;
}

/* Tags */
.tags-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.tags-label {
  font-size: 12px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.tag-chip {
  padding: 6px 14px;
  border: 1px solid #e5e5e5;
  border-radius: 20px;
  background: #fff;
  font-size: 13px;
  color: #333;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
}

.tag-chip:hover {
  border-color: #00bfa5;
  color: #00bfa5;
}

.tag-chip--active {
  background: #00bfa5;
  color: #fff;
  border-color: #00bfa5;
}

/* Category cards */
.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.cat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: all 0.15s;
}

.cat-card:hover {
  border-color: #00bfa5;
  box-shadow: 0 2px 8px rgba(0, 191, 165, 0.08);
}

.cat-card--selected {
  border-color: #00bfa5;
  background: rgba(0, 191, 165, 0.04);
}

.cat-card--all {
  border-style: dashed;
}

.cat-icon {
  font-size: 28px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border-radius: 10px;
  flex-shrink: 0;
}

.cat-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cat-name {
  font-size: 14px;
  font-weight: 600;
  color: #111;
}

.cat-desc {
  font-size: 12px;
  color: #888;
}

/* Full list */
.full-list {
  margin-bottom: 24px;
}

.topic-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #eee;
  border-radius: 12px;
}

.topic-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f5f5f5;
  transition: background 0.1s;
  font-size: 14px;
  color: #333;
}

.topic-item:last-child {
  border-bottom: none;
}

.topic-item:hover {
  background: #f0fdf9;
}

.topic-item--selected {
  background: #f0fdf9;
  font-weight: 500;
  color: #00bfa5;
}

.topic-empty {
  padding: 24px;
  text-align: center;
  color: #999;
  font-size: 14px;
}

.back-btn {
  margin-top: 12px;
  padding: 8px 16px;
  border: none;
  background: none;
  color: #666;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
}

.back-btn:hover {
  color: #00bfa5;
}

/* Selection bar */
.selection-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: #f0fdf9;
  border: 1px solid #d1fae5;
  border-radius: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selection-label {
  font-size: 13px;
  color: #666;
}

.selection-name {
  font-size: 15px;
  font-weight: 600;
  color: #111;
}

.period-toggle {
  display: flex;
  gap: 6px;
}

.period-btn {
  padding: 8px 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  color: #333;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.15s;
}

.period-btn:hover {
  border-color: #00bfa5;
}

.period-btn--active {
  background: #111;
  color: #fff;
  border-color: #111;
}

.period-btn--paid .paid-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #00bfa5;
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  margin-left: 4px;
  vertical-align: middle;
}

/* Error */
.error-msg {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 12px 16px;
  font-size: 14px;
  margin-bottom: 16px;
}

/* Limit */
.limit-block {
  background: #fef9e7;
  border: 1px solid #fde68a;
  border-radius: 10px;
  padding: 14px 16px;
  font-size: 14px;
  color: #92400e;
  margin-bottom: 16px;
}

/* Action row */
.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.remaining {
  font-size: 13px;
  color: #888;
}

.remaining strong {
  color: #00bfa5;
}

.start-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 32px;
  border: none;
  border-radius: 10px;
  background: #111;
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.15s;
}

.start-btn:hover:not(:disabled) {
  opacity: 0.85;
}

.start-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* Loading */
.list-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px;
  color: #888;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid #e5e5e5;
  border-top-color: #00bfa5;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

.spinner--sm {
  width: 14px;
  height: 14px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Footer */
.footer {
  padding: 20px 24px;
  border-top: 1px solid #eee;
  background: #fff;
}

.footer-container {
  max-width: 1100px;
  margin: 0 auto;
}

.footer-copy {
  font-size: 13px;
  color: #999;
}

/* Responsive */
@media (max-width: 768px) {
  .card {
    padding: 24px;
  }

  .card-title {
    font-size: 22px;
  }

  .categories-grid {
    grid-template-columns: 1fr;
  }

  .selection-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-row {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
  }

  .start-btn {
    justify-content: center;
  }
}
</style>
