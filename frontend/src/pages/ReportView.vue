<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
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

const isNiche = computed(() => report.value?.analysis_mode === 'niche_search' && report.value?.niche_data)

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

function sourcesLabel(sources?: string): string {
  if (!sources) return 'Pikabu'
  if (sources === 'pikabu,habr,vcru') return 'Pikabu + Habr + VC.ru'
  if (sources === 'pikabu,habr') return 'Pikabu + Habr'
  if (sources === 'vcru') return 'VC.ru'
  if (sources === 'habr') return 'Habr'
  return 'Pikabu'
}

function sourcesBadgeClass(sources?: string): string {
  if (!sources || sources === 'pikabu') return 'rv-src-badge--pikabu'
  if (sources === 'habr') return 'rv-src-badge--habr'
  if (sources === 'vcru') return 'rv-src-badge--vcru'
  return 'rv-src-badge--both'
}

function postPlatformLabel(url: string): string {
  if (url.includes('habr.com')) return 'Открыть на Habr ↗'
  if (url.includes('vc.ru')) return 'Открыть на VC.ru ↗'
  return 'Открыть на Pikabu ↗'
}

function frequencyColor(freq: string): string {
  if (freq === 'Массово') return 'rv-freq--mass'
  if (freq === 'Часто') return 'rv-freq--often'
  if (freq === 'Периодически') return 'rv-freq--periodic'
  return 'rv-freq--rare'
}

function goBack() {
  router.push({ name: 'reports', params: { topicId: String(topicId) } })
}

onMounted(loadReport)
</script>

<template>
  <div class="rv-page">
    <header class="rv-header">
      <h1 class="rv-title">{{ isNiche ? 'Отчёт: Поиск ниши' : 'Отчёт по анализу' }}</h1>
      <button class="rv-back" @click="goBack">← Назад к списку отчётов</button>
    </header>

    <div v-if="loading" class="rv-loading">
      <div class="rv-spinner"></div>
      <span>Загрузка отчёта…</span>
    </div>

    <div v-else-if="error" class="rv-error" role="alert">
      <p>{{ error }}</p>
      <button class="rv-btn rv-btn--secondary" @click="goBack">Вернуться</button>
    </div>

    <template v-else-if="report">
      <p class="rv-date">
        <span class="rv-src-badge" :class="sourcesBadgeClass(report.sources)">
          {{ sourcesLabel(report.sources) }}
        </span>
        Сгенерирован: {{ formatDate(report.generated_at) }}
      </p>

      <!-- ===== NICHE SEARCH REPORT ===== -->
      <template v-if="isNiche && report.niche_data">

        <!-- Key Pains -->
        <section class="rv-section">
          <h2 class="rv-section-title">🔥 ТОП Ключевых болей</h2>
          <div v-if="report.niche_data.key_pains.length === 0" class="rv-empty">Нет данных</div>
          <ul v-else class="rv-list">
            <li v-for="(pain, i) in report.niche_data.key_pains" :key="i" class="rv-card">
              <div class="rv-card-header">
                <span class="rv-card-name">{{ pain.description }}</span>
                <div class="rv-badges">
                  <span class="rv-badge" :class="frequencyColor(pain.frequency)">{{ pain.frequency }}</span>
                  <span class="rv-badge" :class="pain.emotional_charge === 'Высокий' ? 'rv-badge--high' : 'rv-badge--medium'">
                    {{ pain.emotional_charge }}
                  </span>
                </div>
              </div>
              <div v-if="pain.examples && pain.examples.length > 0" class="rv-examples">
                <span class="rv-examples-label">Цитаты:</span>
                <ul class="rv-examples-list">
                  <li v-for="(ex, j) in pain.examples" :key="j">«{{ ex }}»</li>
                </ul>
              </div>
            </li>
          </ul>
        </section>

        <!-- JTBD Analysis -->
        <section class="rv-section">
          <h2 class="rv-section-title">🕵️ JTBD-Анализ</h2>
          <div v-if="report.niche_data.jtbd_analyses.length === 0" class="rv-empty">Нет данных</div>
          <ul v-else class="rv-list">
            <li v-for="(jtbd, i) in report.niche_data.jtbd_analyses" :key="i" class="rv-card rv-card--jtbd">
              <h3 class="rv-jtbd-title">{{ jtbd.pain_description }}</h3>
              <dl class="rv-jtbd-grid">
                <dt>🎯 Контекст</dt>
                <dd>{{ jtbd.situational }}</dd>
                <dt>⚙️ Функциональная задача</dt>
                <dd>{{ jtbd.functional }}</dd>
                <dt>💭 Эмоциональная задача</dt>
                <dd>{{ jtbd.emotional }}</dd>
                <dt>🔧 Текущее решение</dt>
                <dd>{{ jtbd.current_solution }}</dd>
              </dl>
            </li>
          </ul>
        </section>

        <!-- Business Ideas -->
        <section class="rv-section">
          <h2 class="rv-section-title">💡 Бизнес-идеи</h2>
          <div v-if="report.niche_data.business_ideas.length === 0" class="rv-empty">Нет данных</div>
          <ul v-else class="rv-list">
            <li v-for="(idea, i) in report.niche_data.business_ideas" :key="i" class="rv-card">
              <div class="rv-card-header">
                <span class="rv-card-name">{{ idea.name }}</span>
              </div>
              <p class="rv-card-desc">{{ idea.description }}</p>
              <div class="rv-mvp">
                <span class="rv-mvp-label">🚀 MVP за выходные:</span>
                <p class="rv-mvp-text">{{ idea.mvp_plan }}</p>
              </div>
            </li>
          </ul>
        </section>

        <!-- Market Trends -->
        <section class="rv-section">
          <h2 class="rv-section-title">🚀 Тренды и рыночный контекст</h2>
          <div v-if="report.niche_data.market_trends.length === 0" class="rv-empty">Нет данных</div>
          <ul v-else class="rv-list">
            <li v-for="(trend, i) in report.niche_data.market_trends" :key="i" class="rv-card">
              <div class="rv-card-header">
                <span class="rv-card-name">{{ trend.name }}</span>
              </div>
              <p class="rv-card-desc">{{ trend.description }}</p>
              <p class="rv-monetization">💰 {{ trend.monetization_hint }}</p>
            </li>
          </ul>
        </section>
      </template>

      <!-- ===== STANDARD TOPIC ANALYSIS REPORT ===== -->
      <template v-else>
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
              <a :href="td.post_url" target="_blank" rel="noopener" class="rv-link">
                {{ postPlatformLabel(td.post_url) }}
              </a>
            </li>
          </ul>
        </section>
      </template>
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
.rv-header { text-align: center; margin-bottom: 24px; }
.rv-title { font-size: 32px; margin: 0 0 12px; }
.rv-back { background: none; border: none; color: var(--accent); font-size: 14px; font-family: var(--sans); cursor: pointer; padding: 0; }
.rv-back:hover { text-decoration: underline; }
.rv-date { text-align: center; font-size: 14px; color: var(--text); margin: 0 0 28px; display: flex; align-items: center; justify-content: center; gap: 10px; }

.rv-src-badge { display: inline-block; font-size: 12px; font-weight: 500; padding: 3px 10px; border-radius: 4px; white-space: nowrap; }
.rv-src-badge--pikabu { background: rgba(76,175,80,0.15); color: #2e7d32; }
.rv-src-badge--habr { background: rgba(33,150,243,0.15); color: #1565c0; }
.rv-src-badge--both { background: var(--accent-bg); color: var(--accent); }
.rv-src-badge--vcru { background: rgba(255,152,0,0.15); color: #e65100; }

.rv-section { margin-bottom: 32px; }
.rv-section-title { font-size: 22px; margin: 0 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.rv-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.rv-card { border: 1px solid var(--border); border-radius: 8px; padding: 16px 20px; display: flex; flex-direction: column; gap: 8px; transition: box-shadow 0.2s; }
.rv-card:hover { box-shadow: var(--shadow); }
.rv-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.rv-card-name { font-weight: 500; color: var(--text-h); font-size: 16px; }
.rv-card-desc { margin: 0; font-size: 15px; color: var(--text); line-height: 1.5; }

.rv-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.rv-badge { font-size: 12px; font-family: var(--mono); padding: 3px 8px; border-radius: 4px; color: var(--accent); background: var(--accent-bg); white-space: nowrap; }
.rv-badge--score { color: #16a34a; background: rgba(22,163,74,0.1); }
.rv-badge--high { color: #b91c1c; background: rgba(185,28,28,0.1); }
.rv-badge--medium { color: #d97706; background: rgba(217,119,6,0.1); }

.rv-freq--mass { color: #b91c1c; background: rgba(185,28,28,0.1); }
.rv-freq--often { color: #d97706; background: rgba(217,119,6,0.1); }
.rv-freq--periodic { color: #2563eb; background: rgba(37,99,235,0.1); }
.rv-freq--rare { color: #6b7280; background: rgba(107,114,128,0.1); }

.rv-examples { margin-top: 4px; }
.rv-examples-label { font-size: 13px; font-weight: 500; color: var(--text-h); }
.rv-examples-list { margin: 4px 0 0; padding-left: 20px; font-size: 14px; color: var(--text); line-height: 1.6; font-style: italic; }

/* JTBD card */
.rv-card--jtbd { gap: 12px; }
.rv-jtbd-title { font-size: 17px; font-weight: 600; margin: 0; color: var(--text-h); }
.rv-jtbd-grid { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; font-size: 14px; }
.rv-jtbd-grid dt { font-weight: 500; color: var(--text-h); white-space: nowrap; }
.rv-jtbd-grid dd { margin: 0; color: var(--text); line-height: 1.5; }

/* MVP block */
.rv-mvp { background: var(--accent-bg); border-radius: 6px; padding: 10px 14px; }
.rv-mvp-label { font-size: 13px; font-weight: 600; color: var(--text-h); }
.rv-mvp-text { margin: 4px 0 0; font-size: 14px; color: var(--text); line-height: 1.5; }

/* Monetization hint */
.rv-monetization { margin: 0; font-size: 14px; color: var(--text); font-style: italic; }

.rv-link { font-size: 14px; color: var(--accent); text-decoration: none; align-self: flex-start; }
.rv-link:hover { text-decoration: underline; }
.rv-empty { text-align: center; color: var(--text); font-size: 14px; padding: 20px; border: 1px dashed var(--border); border-radius: 8px; }

.rv-error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 16px; font-size: 14px; text-align: left; }
.rv-error p { margin: 0 0 8px; }
.rv-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 24px; border: none; border-radius: 8px; background: var(--accent); color: #fff; font-size: 15px; font-family: var(--sans); font-weight: 500; cursor: pointer; transition: opacity 0.2s; }
.rv-btn:hover:not(:disabled) { opacity: 0.9; }
.rv-btn--secondary { background: transparent; color: var(--text-h); border: 1px solid var(--border); }
.rv-btn--secondary:hover { background: var(--accent-bg); }

.rv-loading { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 40px; color: var(--text); }
.rv-spinner { width: 20px; height: 20px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: rv-spin 0.6s linear infinite; }
@keyframes rv-spin { to { transform: rotate(360deg); } }

@media (prefers-color-scheme: dark) {
  .rv-src-badge--pikabu { background: rgba(76,175,80,0.2); color: #81c784; }
  .rv-src-badge--habr { background: rgba(33,150,243,0.2); color: #64b5f6; }
  .rv-src-badge--vcru { background: rgba(255,152,0,0.2); color: #ffb74d; }
  .rv-badge--score { color: #4ade80; background: rgba(74,222,128,0.15); }
  .rv-badge--high { color: #fca5a5; background: rgba(185,28,28,0.15); }
  .rv-badge--medium { color: #fbbf24; background: rgba(217,119,6,0.15); }
  .rv-freq--mass { color: #fca5a5; background: rgba(185,28,28,0.15); }
  .rv-freq--often { color: #fbbf24; background: rgba(217,119,6,0.15); }
  .rv-freq--periodic { color: #93c5fd; background: rgba(37,99,235,0.15); }
  .rv-error { background: rgba(185,28,28,0.15); color: #fca5a5; border-color: rgba(185,28,28,0.3); }
}
</style>
