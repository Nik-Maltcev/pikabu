<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReport, createPayment, checkPayment } from '../api/client'
import type { Report } from '../types/api'

const route = useRoute()
const router = useRouter()

const topicId = Number(route.params.topicId)
const reportId = Number(route.params.reportId)

const report = ref<Report | null>(null)
const loading = ref(true)
const error = ref('')
const isPaid = ref(false)
const paymentLoading = ref(false)

const FREE_PAINS = 3
const FREE_IDEAS = 2

const isNiche = computed(() => report.value?.analysis_mode === 'niche_search' && report.value?.niche_data)

function frequencyColor(freq: string): string {
  if (freq === 'Массово') return 'rv-freq--mass'
  if (freq === 'Часто') return 'rv-freq--often'
  if (freq === 'Периодически') return 'rv-freq--periodic'
  return 'rv-freq--rare'
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function loadReport() {
  loading.value = true
  error.value = ''
  try {
    report.value = await getReport(topicId, reportId)
    // Check payment status
    const token = (route.query.token as string) || ''
    const payStatus = await checkPayment(reportId, token, topicId)
    isPaid.value = payStatus.paid
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось загрузить отчёт'
  } finally {
    loading.value = false
  }
}

async function onBuyReport() {
  paymentLoading.value = true
  try {
    const result = await createPayment(reportId)
    // Redirect to Robokassa
    window.location.href = result.payment_url
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка создания платежа'
  } finally {
    paymentLoading.value = false
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
      <p class="rv-date">Сгенерирован: {{ formatDate(report.generated_at) }}</p>

      <!-- ===== NICHE SEARCH REPORT ===== -->
      <template v-if="isNiche && report.niche_data">

        <!-- Key Pains (first FREE_PAINS free) -->
        <section class="rv-section">
          <h2 class="rv-section-title">🔥 ТОП Ключевых болей</h2>
          <div v-if="report.niche_data.key_pains.length === 0" class="rv-empty">Нет данных</div>
          <ul v-else class="rv-list">
            <li v-for="(pain, i) in report.niche_data.key_pains" :key="i" class="rv-card" :class="{ 'rv-blurred': !isPaid && i >= FREE_PAINS }">
              <div class="rv-card-header">
                <span class="rv-card-name">{{ !isPaid && i >= FREE_PAINS ? '████████ ██████' : pain.description }}</span>
                <div class="rv-badges">
                  <span class="rv-badge" :class="frequencyColor(pain.frequency)">{{ pain.frequency }}</span>
                  <span class="rv-badge" :class="pain.emotional_charge === 'Высокий' ? 'rv-badge--high' : 'rv-badge--medium'">{{ pain.emotional_charge }}</span>
                </div>
              </div>
              <div v-if="(isPaid || i < FREE_PAINS) && pain.examples && pain.examples.length > 0" class="rv-examples">
                <span class="rv-examples-label">Цитаты:</span>
                <ul class="rv-examples-list">
                  <li v-for="(ex, j) in pain.examples" :key="j">«{{ ex }}»</li>
                </ul>
              </div>
            </li>
          </ul>
        </section>

        <!-- JTBD Analysis (paid only) -->
        <section class="rv-section" :class="{ 'rv-section--locked': !isPaid }">
          <h2 class="rv-section-title">🕵️ JTBD-Анализ <span v-if="!isPaid" class="rv-lock-badge">🔒 Платный раздел</span></h2>
          <template v-if="isPaid">
            <div v-if="report.niche_data.jtbd_analyses.length === 0" class="rv-empty">Нет данных</div>
            <ul v-else class="rv-list">
              <li v-for="(jtbd, i) in report.niche_data.jtbd_analyses" :key="i" class="rv-card rv-card--jtbd">
                <h3 class="rv-jtbd-title">{{ jtbd.pain_description }}</h3>
                <dl class="rv-jtbd-grid">
                  <dt>🎯 Контекст</dt><dd>{{ jtbd.situational }}</dd>
                  <dt>⚙️ Функциональная задача</dt><dd>{{ jtbd.functional }}</dd>
                  <dt>💭 Эмоциональная задача</dt><dd>{{ jtbd.emotional }}</dd>
                  <dt>🔧 Текущее решение</dt><dd>{{ jtbd.current_solution }}</dd>
                </dl>
              </li>
            </ul>
          </template>
          <div v-else class="rv-locked-placeholder">
            <p>JTBD-анализ доступен в полном отчёте</p>
          </div>
        </section>

        <!-- Business Ideas (first FREE_IDEAS free, rest blurred) -->
        <section class="rv-section">
          <h2 class="rv-section-title">💡 Бизнес-идеи</h2>
          <div v-if="report.niche_data.business_ideas.length === 0" class="rv-empty">Нет данных</div>
          <ul v-else class="rv-list">
            <li v-for="(idea, i) in report.niche_data.business_ideas" :key="i" class="rv-card" :class="{ 'rv-blurred': !isPaid && i >= FREE_IDEAS }">
              <div class="rv-card-header">
                <span class="rv-card-name">{{ !isPaid && i >= FREE_IDEAS ? '████████ ██████' : idea.name }}</span>
                <div v-if="isPaid || i < FREE_IDEAS" class="rv-badges">
                  <span v-if="idea.demand_level" class="rv-badge rv-badge--score">Спрос: {{ idea.demand_level }}</span>
                  <span v-if="idea.competition_level" class="rv-badge">Конкуренция: {{ idea.competition_level }}</span>
                </div>
              </div>
              <template v-if="isPaid || i < FREE_IDEAS">
                <p class="rv-card-desc">{{ idea.description }}</p>
                <!-- Paid-only fields -->
                <template v-if="isPaid">
                  <div class="rv-mvp">
                    <span class="rv-mvp-label">🚀 MVP за выходные:</span>
                    <p class="rv-mvp-text">{{ idea.mvp_plan }}</p>
                  </div>
                  <div v-if="idea.launch_recommendations?.length" class="rv-detail-block">
                    <span class="rv-detail-label">📋 Рекомендации по запуску:</span>
                    <ul class="rv-detail-list"><li v-for="(r, j) in idea.launch_recommendations" :key="j">{{ r }}</li></ul>
                  </div>
                  <div v-if="idea.risks?.length" class="rv-detail-block">
                    <span class="rv-detail-label">⚠️ Риски:</span>
                    <ul class="rv-detail-list"><li v-for="(r, j) in idea.risks" :key="j">{{ r }}</li></ul>
                  </div>
                  <div v-if="idea.positioning" class="rv-detail-block">
                    <span class="rv-detail-label">🎯 Позиционирование:</span>
                    <p class="rv-detail-text">{{ idea.positioning }}</p>
                  </div>
                  <div v-if="idea.search_queries?.length" class="rv-detail-block">
                    <span class="rv-detail-label">🔍 Поисковые запросы:</span>
                    <div class="rv-tags"><span v-for="(q, j) in idea.search_queries" :key="j" class="rv-tag">{{ q }}</span></div>
                  </div>
                  <div v-if="idea.entry_difficulty" class="rv-detail-block">
                    <span class="rv-detail-label">📊 Сложность входа:</span>
                    <span class="rv-badge">{{ idea.entry_difficulty }}</span>
                  </div>
                </template>
              </template>
            </li>
          </ul>
        </section>

        <!-- Market Trends (paid only) -->
        <section class="rv-section" :class="{ 'rv-section--locked': !isPaid }">
          <h2 class="rv-section-title">🚀 Тренды <span v-if="!isPaid" class="rv-lock-badge">🔒 Платный раздел</span></h2>
          <template v-if="isPaid">
            <div v-if="report.niche_data.market_trends.length === 0" class="rv-empty">Нет данных</div>
            <ul v-else class="rv-list">
              <li v-for="(trend, i) in report.niche_data.market_trends" :key="i" class="rv-card">
                <div class="rv-card-header"><span class="rv-card-name">{{ trend.name }}</span></div>
                <p class="rv-card-desc">{{ trend.description }}</p>
                <p class="rv-monetization">💰 {{ trend.monetization_hint }}</p>
              </li>
            </ul>
          </template>
          <div v-else class="rv-locked-placeholder">
            <p>Тренды и рыночный контекст доступны в полном отчёте</p>
          </div>
        </section>

        <!-- PAYWALL CTA -->
        <section v-if="!isPaid" class="rv-paywall">
          <div class="rv-paywall-inner">
            <h2 class="rv-paywall-title">🔓 Откройте полный отчёт</h2>
            <p class="rv-paywall-desc">Получите доступ ко всем нишам, JTBD-анализу, рекомендациям по запуску, рискам, позиционированию и поисковым запросам.</p>
            <button class="rv-btn rv-btn--pay" :disabled="paymentLoading" @click="onBuyReport">
              <template v-if="paymentLoading">Переход к оплате…</template>
              <template v-else>Открыть полный отчёт — 4 990 ₽</template>
            </button>
            <p class="rv-paywall-hint">Оплата через Робокассу · Карта, СБП, кошельки</p>
          </div>
        </section>

      </template>

      <!-- ===== STANDARD REPORT (no paywall) ===== -->
      <template v-else>
        <section class="rv-section">
          <h2 class="rv-section-title">🔥 Часто обсуждаемые темы</h2>
          <ul v-if="report.hot_topics.length" class="rv-list">
            <li v-for="(ht, i) in report.hot_topics" :key="i" class="rv-card">
              <div class="rv-card-header"><span class="rv-card-name">{{ ht.name }}</span><span class="rv-badge">{{ ht.mentions_count }} упоминаний</span></div>
              <p class="rv-card-desc">{{ ht.description }}</p>
            </li>
          </ul>
          <div v-else class="rv-empty">Нет данных</div>
        </section>
        <section class="rv-section">
          <h2 class="rv-section-title">⚠️ Проблемы пользователей</h2>
          <ul v-if="report.user_problems.length" class="rv-list">
            <li v-for="(up, i) in report.user_problems" :key="i" class="rv-card">
              <p class="rv-card-desc">{{ up.description }}</p>
              <div v-if="up.examples.length" class="rv-examples">
                <ul class="rv-examples-list"><li v-for="(ex, j) in up.examples" :key="j">{{ ex }}</li></ul>
              </div>
            </li>
          </ul>
          <div v-else class="rv-empty">Нет данных</div>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.rv-page {
  --text: #6b7280;
  --text-h: #1b1b1d;
  --border: #e5e5e5;
  --accent: #7c3aed;
  --accent-bg: #f5f3ff;
  max-width: 800px; margin: 0 auto; padding: 40px 24px; min-height: 100vh;
}
.rv-header { text-align: center; margin-bottom: 24px; }
.rv-title { font-size: 28px; margin: 0 0 12px; color: var(--text-h); }
.rv-back { background: none; border: none; color: var(--accent); font-size: 14px; cursor: pointer; padding: 0; }
.rv-back:hover { text-decoration: underline; }
.rv-date { text-align: center; font-size: 14px; color: var(--text); margin: 0 0 28px; }

.rv-section { margin-bottom: 32px; }
.rv-section-title { font-size: 20px; margin: 0 0 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border); color: var(--text-h); display: flex; align-items: center; gap: 8px; }
.rv-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.rv-card { border: 1px solid var(--border); border-radius: 8px; padding: 16px 20px; display: flex; flex-direction: column; gap: 8px; transition: box-shadow 0.2s; }
.rv-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.rv-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.rv-card-name { font-weight: 500; color: var(--text-h); font-size: 16px; }
.rv-card-desc { margin: 0; font-size: 15px; color: var(--text); line-height: 1.5; }

.rv-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.rv-badge { font-size: 12px; padding: 3px 8px; border-radius: 4px; color: var(--accent); background: var(--accent-bg); white-space: nowrap; }
.rv-badge--score { color: #16a34a; background: rgba(22,163,74,0.1); }
.rv-badge--high { color: #b91c1c; background: rgba(185,28,28,0.1); }
.rv-badge--medium { color: #d97706; background: rgba(217,119,6,0.1); }

.rv-examples { margin-top: 4px; }
.rv-examples-label { font-size: 13px; font-weight: 500; color: var(--text-h); }
.rv-examples-list { margin: 4px 0 0; padding-left: 20px; font-size: 14px; color: var(--text); line-height: 1.6; font-style: italic; }

.rv-card--jtbd { gap: 12px; }
.rv-jtbd-title { font-size: 17px; font-weight: 600; margin: 0; color: var(--text-h); }
.rv-jtbd-grid { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; font-size: 14px; }
.rv-jtbd-grid dt { font-weight: 500; color: var(--text-h); white-space: nowrap; }
.rv-jtbd-grid dd { margin: 0; color: var(--text); line-height: 1.5; }

.rv-mvp { background: var(--accent-bg); border-radius: 6px; padding: 10px 14px; }
.rv-mvp-label { font-size: 13px; font-weight: 600; color: var(--text-h); }
.rv-mvp-text { margin: 4px 0 0; font-size: 14px; color: var(--text); line-height: 1.5; }

.rv-detail-block { margin-top: 8px; }
.rv-detail-label { font-size: 13px; font-weight: 600; color: var(--text-h); display: block; margin-bottom: 4px; }
.rv-detail-list { margin: 0; padding-left: 20px; font-size: 14px; color: var(--text); line-height: 1.6; }
.rv-detail-text { margin: 0; font-size: 14px; color: var(--text); line-height: 1.5; }
.rv-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
.rv-tag { font-size: 12px; padding: 4px 10px; border-radius: 4px; background: var(--accent-bg); color: var(--accent); }

.rv-monetization { margin: 0; font-size: 14px; color: var(--text); font-style: italic; }
.rv-empty { text-align: center; color: var(--text); font-size: 14px; padding: 20px; border: 1px dashed var(--border); border-radius: 8px; }
.rv-error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 8px; padding: 12px 16px; font-size: 14px; }
.rv-error p { margin: 0 0 8px; }

/* Blurred / locked */
.rv-blurred { filter: blur(4px); pointer-events: none; user-select: none; opacity: 0.6; }
.rv-section--locked { opacity: 0.5; }
.rv-lock-badge { font-size: 13px; font-weight: 400; color: var(--text); }
.rv-locked-placeholder { text-align: center; padding: 24px; border: 1px dashed var(--border); border-radius: 8px; color: var(--text); font-size: 14px; }

/* Paywall CTA */
.rv-paywall { margin-top: 16px; }
.rv-paywall-inner { text-align: center; padding: 32px 24px; border: 2px solid #7c3aed; border-radius: 12px; background: #f5f3ff; }
.rv-paywall-title { font-size: 24px; margin: 0 0 8px; color: #1b1b1d; }
.rv-paywall-desc { font-size: 15px; color: #6b7280; margin: 0 0 20px; max-width: 500px; margin-left: auto; margin-right: auto; line-height: 1.5; }
.rv-btn--pay { display: inline-flex; align-items: center; justify-content: center; padding: 14px 32px; border: none; border-radius: 10px; background: #7c3aed; color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; transition: opacity 0.15s; }
.rv-btn--pay:hover:not(:disabled) { opacity: 0.9; }
.rv-btn--pay:disabled { opacity: 0.5; cursor: not-allowed; }
.rv-paywall-hint { font-size: 12px; color: #6b7280; margin: 12px 0 0; }

.rv-btn { display: inline-flex; align-items: center; padding: 10px 20px; border: none; border-radius: 8px; background: var(--accent); color: #fff; font-size: 14px; cursor: pointer; }
.rv-btn--secondary { background: transparent; color: var(--text-h); border: 1px solid var(--border); }

.rv-loading { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 40px; color: var(--text); }
.rv-spinner { width: 20px; height: 20px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: rv-spin 0.6s linear infinite; }
@keyframes rv-spin { to { transform: rotate(360deg); } }

.rv-freq--mass { color: #b91c1c; background: rgba(185,28,28,0.1); }
.rv-freq--often { color: #d97706; background: rgba(217,119,6,0.1); }
.rv-freq--periodic { color: #2563eb; background: rgba(37,99,235,0.1); }
.rv-freq--rare { color: #6b7280; background: rgba(107,114,128,0.1); }
</style>
