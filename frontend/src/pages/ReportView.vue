<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReport, createPayment, checkPayment, checkPromoCode, askQuestion } from '../api/client'
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
const promoCode = ref('')
const promoApplied = ref(false)
const promoPrice = ref(0)
const promoDiscount = ref(0)
const promoError = ref('')

const FREE_PAINS = 3
const FREE_IDEAS = 2

// Chat state
const chatInput = ref('')
const chatLoading = ref(false)
const chatRemaining = ref(3)
const chatMessages = ref<{ role: 'user' | 'ai'; text: string }[]>([])
const chatAccessToken = ref('')

async function onAskChat() {
  if (!chatInput.value.trim() || chatLoading.value || chatRemaining.value <= 0) return
  const question = chatInput.value.trim()
  chatMessages.value.push({ role: 'user', text: question })
  chatInput.value = ''
  chatLoading.value = true
  try {
    const res = await askQuestion(topicId, question, chatAccessToken.value)
    chatMessages.value.push({ role: 'ai', text: res.answer })
    chatRemaining.value = res.questions_remaining
  } catch (e: any) {
    chatMessages.value.push({ role: 'ai', text: e?.response?.data?.detail || 'Ошибка' })
  } finally {
    chatLoading.value = false
  }
}

const isNiche = computed(() => report.value?.analysis_mode === 'niche_search' && report.value?.niche_data)

// Risk category icons mapping
const RISK_CATEGORY_ICONS: Record<string, string> = {
  'Market Risk': '📈',
  'Product Risk': '🛠️',
  'Customer Risk': '👥',
  'Execution Risk': '⚡',
  'Financial Risk': '💰',
}

function riskCategoryIcon(category: string): string {
  return RISK_CATEGORY_ICONS[category] || '⚠️'
}

interface RiskObject {
  category: string
  description: string
  mitigation: string
}

interface RiskGroup {
  category: string
  risks: RiskObject[]
}

function groupRisksByCategory(risks: RiskObject[]): RiskGroup[] {
  const groups: Record<string, RiskObject[]> = {}
  for (const risk of risks) {
    if (!groups[risk.category]) {
      groups[risk.category] = []
    }
    groups[risk.category].push(risk)
  }
  // Preserve the order of first appearance
  const result: RiskGroup[] = []
  const seen = new Set<string>()
  for (const risk of risks) {
    if (!seen.has(risk.category)) {
      seen.add(risk.category)
      result.push({ category: risk.category, risks: groups[risk.category] })
    }
  }
  return result
}

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

const SOURCE_LABELS: Record<string, string> = {
  pikabu: 'Пикабу',
  habr: 'Хабр',
  vcru: 'VC.ru',
}

function formatSources(sources: string): string {
  return sources.split(',').map(s => SOURCE_LABELS[s.trim()] || s.trim()).join(', ')
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
    if (payStatus.paid && payStatus.access_token) {
      chatAccessToken.value = payStatus.access_token
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось загрузить отчёт'
  } finally {
    loading.value = false
  }
}

async function onApplyPromo() {
  promoError.value = ''
  if (!promoCode.value.trim()) return
  try {
    const res = await checkPromoCode(promoCode.value.trim())
    if (res.valid) {
      promoApplied.value = true
      promoPrice.value = res.price!
      promoDiscount.value = res.discount_percent!
    } else {
      promoError.value = 'Промокод не найден'
      promoApplied.value = false
    }
  } catch {
    promoError.value = 'Ошибка проверки промокода'
  }
}

async function onBuyReport() {
  paymentLoading.value = true
  try {
    const code = promoApplied.value ? promoCode.value.trim() : undefined
    const result = await createPayment(reportId, code)
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

        <!-- Key Pains & Mention Rating — two visually distinct blocks -->
        <section class="rv-section">
          <div class="grid grid-cols-1 lg:grid-cols-[1fr_1px_1fr] gap-6 lg:gap-0">
            <!-- Left: Key Pains Section -->
            <div class="bg-emerald-50 rounded-2xl p-6 lg:rounded-r-none">
              <h2 class="rv-section-title">🔥 ТОП Ключевых болей</h2>
              <p class="text-sm text-gray-500 -mt-3 mb-4 pl-4">Формулировки проблем с цитатами</p>
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
            </div>
            <!-- Vertical divider (visible only at lg+) -->
            <div class="hidden lg:block bg-gray-300"></div>
            <!-- Right: Mention Rating Section -->
            <div class="bg-slate-50 rounded-2xl p-6 lg:rounded-l-none">
              <h2 class="rv-section-title">📊 Рейтинг упоминаний</h2>
              <p class="text-sm text-gray-500 -mt-3 mb-4 pl-4">Количественная частота упоминаний</p>
              <div v-if="report.niche_data.key_pains.length === 0" class="rv-empty">Нет данных</div>
              <div v-else class="rv-mentions-list">
                <div v-for="(pain, i) in report.niche_data.key_pains" :key="'m'+i" class="rv-mention-row" :class="{ 'rv-blurred': !isPaid && i >= FREE_PAINS }">
                  <div class="rv-mention-bar-wrap">
                    <div class="rv-mention-label">{{ !isPaid && i >= FREE_PAINS ? '████' : pain.description }}</div>
                    <div class="rv-mention-bar-bg">
                      <div class="rv-mention-bar-fill" :style="{ width: Math.min(100, (pain.mentions_count || 0) / Math.max(...report.niche_data.key_pains.map(p => p.mentions_count || 1)) * 100) + '%' }"></div>
                    </div>
                  </div>
                  <span class="rv-mention-count">{{ pain.mentions_count || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
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
                  <!-- Analogues sub-block -->
                  <div class="mt-4 mb-4">
                    <h4 class="text-sm font-bold text-gray-800 mb-3">🏢 Аналоги на рынке</h4>
                    <!-- Error state: analogues is undefined/null -->
                    <p v-if="idea.analogues === undefined || idea.analogues === null" class="text-sm text-gray-500 italic">
                      Данные об аналогах временно недоступны
                    </p>
                    <!-- Empty state: analogues array is empty -->
                    <p v-else-if="idea.analogues.length === 0" class="text-sm text-emerald-600 font-medium">
                      Аналоги не найдены — рынок может быть незанят
                    </p>
                    <!-- Analogues data -->
                    <div v-else class="flex flex-col gap-3">
                      <div
                        v-for="(analogue, ai) in idea.analogues"
                        :key="ai"
                        class="rounded-lg border border-gray-100 bg-gray-50 p-3"
                      >
                        <div class="flex items-center gap-2 mb-1">
                          <span class="font-semibold text-sm text-gray-800">{{ analogue.company_name }}</span>
                          <span v-if="analogue.has_ru_competitor" class="text-xs px-1.5 py-0.5 rounded bg-blue-50 border border-blue-200" title="Есть конкурент в РФ">🇷🇺</span>
                        </div>
                        <p class="text-sm text-gray-600 mb-1">{{ analogue.description }}</p>
                        <div class="flex flex-wrap gap-2 text-xs text-gray-500">
                          <span v-if="analogue.annual_revenue">💰 {{ analogue.annual_revenue }}</span>
                          <span v-if="analogue.investment_round">📈 Раунд: {{ analogue.investment_round }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <!-- Horizontal divider separating analogues from MVP plan (16px margin) -->
                  <hr class="border-t border-gray-200 my-4" />

                  <div class="rv-mvp">
                    <span class="rv-mvp-label">🚀 MVP за выходные:</span>
                    <p class="rv-mvp-text">{{ idea.mvp_plan }}</p>
                  </div>
                  <div v-if="idea.launch_recommendations?.length" class="rv-detail-block">
                    <span class="rv-detail-label">📋 Рекомендации по запуску:</span>
                    <ol class="rv-recommendations-list">
                      <li v-for="(r, j) in idea.launch_recommendations" :key="j" class="rv-recommendation-item">
                        <span class="rv-recommendation-number">{{ j + 1 }}</span>
                        <span class="rv-recommendation-text">
                          <span v-if="r.match(/^За\s+\d+\s+(дней|недель|день|дня|неделю|недели):/)" class="rv-recommendation-timeframe">{{ r.match(/^(За\s+\d+\s+(?:дней|недель|день|дня|неделю|недели):)/)?.[1] }}</span>
                          <span>{{ r.match(/^За\s+\d+\s+(?:дней|недель|день|дня|неделю|недели):\s*(.*)$/)?.[1] || r }}</span>
                        </span>
                      </li>
                    </ol>
                  </div>
                  <div v-if="idea.risks?.length" class="rv-risks-section">
                    <span class="rv-detail-label">⚠️ Риски:</span>
                    <!-- Structured risks (Risk objects grouped by category) -->
                    <template v-if="typeof idea.risks[0] === 'object' && idea.risks[0] !== null && 'category' in idea.risks[0]">
                      <div v-for="(group, gIdx) in groupRisksByCategory(idea.risks)" :key="gIdx" class="rv-risk-group">
                        <h4 class="rv-risk-category-heading">
                          <span class="rv-risk-category-icon">{{ riskCategoryIcon(group.category) }}</span>
                          {{ group.category }}
                        </h4>
                        <ul class="rv-risk-list">
                          <li v-for="(risk, rIdx) in group.risks" :key="rIdx" class="rv-risk-item">
                            <p class="rv-risk-description">{{ risk.description }}</p>
                            <p class="rv-risk-mitigation"><span class="rv-risk-mitigation-label">Митигация:</span> {{ risk.mitigation }}</p>
                          </li>
                        </ul>
                      </div>
                    </template>
                    <!-- Backward compatibility: plain string risks (old format) -->
                    <template v-else>
                      <ul class="rv-detail-list"><li v-for="(r, j) in idea.risks" :key="j">{{ r }}</li></ul>
                    </template>
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
                <div class="rv-card-header">
                  <span class="rv-card-name">{{ trend.name }}</span>
                  <span v-if="trend.data_source_label" class="rv-badge-ai">ИИ-оценка</span>
                </div>
                <p class="rv-card-desc">{{ trend.description }}</p>
                <p v-if="trend.market_volume_estimate && trend.growth_rate_percent != null" class="rv-market-data">
                  📈 Объём рынка: ~{{ trend.market_volume_estimate }}, Рост: +{{ trend.growth_rate_percent }}% г/г с учётом инфляции
                </p>
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
            
            <!-- Promo code -->
            <div class="rv-promo">
              <div class="rv-promo-row">
                <input v-model="promoCode" type="text" placeholder="Промокод" class="rv-promo-input" @keyup.enter="onApplyPromo" />
                <button class="rv-promo-btn" @click="onApplyPromo">Применить</button>
              </div>
              <p v-if="promoApplied" class="rv-promo-success">✓ Скидка {{ promoDiscount }}% применена</p>
              <p v-if="promoError" class="rv-promo-error">{{ promoError }}</p>
            </div>

            <button class="rv-btn rv-btn--pay" :disabled="paymentLoading" @click="onBuyReport">
              <template v-if="paymentLoading">Переход к оплате…</template>
              <template v-else-if="promoApplied">Открыть полный отчёт — {{ promoPrice.toLocaleString() }} ₽ <span style="text-decoration:line-through;opacity:0.6;margin-left:8px">1 490 ₽</span></template>
              <template v-else>Открыть полный отчёт — 1 490 ₽</template>
            </button>
            <p class="rv-paywall-hint">Оплата через Робокассу · Карта, СБП, кошельки</p>
          </div>
        </section>

        <!-- Chat Widget (paid only) -->
        <section v-if="isPaid" class="rv-section">
          <h2 class="rv-section-title">💬 Спросить у ИИ</h2>
          <!-- Context: sources and data volume -->
          <div class="rv-chat-context">
            <span class="rv-chat-context-item" v-if="report.posts_count">
              📄 {{ report.posts_count.toLocaleString('ru-RU') }} постов
            </span>
            <span class="rv-chat-context-item" v-if="report.comments_count">
              💬 {{ report.comments_count.toLocaleString('ru-RU') }} комментариев
            </span>
            <span class="rv-chat-context-item" v-if="report.sources">
              🌐 {{ formatSources(report.sources) }}
            </span>
          </div>
          <p class="rv-chat-hint">Задайте вопрос по собранным данным ({{ chatRemaining }} из 3 вопросов осталось)</p>
          <div class="rv-chat-box">
            <div v-for="(msg, i) in chatMessages" :key="i" class="rv-chat-msg" :class="msg.role === 'user' ? 'rv-chat-msg--user' : 'rv-chat-msg--ai'">
              <span class="rv-chat-role">{{ msg.role === 'user' ? 'Вы:' : 'ИИ:' }}</span>
              <p class="rv-chat-text">{{ msg.text }}</p>
            </div>
          </div>
          <div v-if="chatRemaining > 0" class="rv-chat-input-row">
            <input v-model="chatInput" type="text" class="rv-chat-input" placeholder="Например: какие боли чаще всего упоминают в комментариях?" @keyup.enter="onAskChat" />
            <button class="rv-chat-send" :disabled="chatLoading || !chatInput.trim()" @click="onAskChat">
              {{ chatLoading ? '...' : '→' }}
            </button>
          </div>
          <p v-else class="rv-chat-exhausted">Лимит вопросов исчерпан</p>
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
  --text: #4b5563;
  --text-h: #111827;
  --border: #e5e7eb;
  --accent: #006a62;
  --accent-light: #ecfdf5;
  --accent-bg: #f0fdf4;
  max-width: 1400px; margin: 0 auto; padding: 40px 20px; min-height: 100vh;
  font-family: 'Inter', system-ui, sans-serif;
}
.rv-header { text-align: center; margin-bottom: 32px; }
.rv-title { font-size: 26px; margin: 0 0 12px; color: var(--text-h); font-weight: 800; }
.rv-back { background: none; border: none; color: var(--accent); font-size: 14px; cursor: pointer; padding: 0; font-weight: 500; }
.rv-back:hover { text-decoration: underline; }
.rv-date { text-align: center; font-size: 13px; color: var(--text); margin: 0 0 32px; background: var(--accent-light); display: inline-block; padding: 6px 16px; border-radius: 20px; }

.rv-section { margin-bottom: 40px; }
.rv-section-title { font-size: 22px; margin: 0 0 20px; padding: 12px 16px; background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%); border-radius: 12px; color: var(--text-h); display: flex; align-items: center; gap: 10px; font-weight: 700; border-left: 4px solid var(--accent); }
.rv-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 16px; }
.rv-card { border: 1px solid var(--border); border-radius: 14px; padding: 20px 24px; display: flex; flex-direction: column; gap: 10px; transition: all 0.2s; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.rv-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); transform: translateY(-1px); }
.rv-card-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.rv-card-name { font-weight: 600; color: var(--text-h); font-size: 17px; line-height: 1.4; }
.rv-card-desc { margin: 0; font-size: 15px; color: var(--text); line-height: 1.6; }

.rv-badges { display: flex; gap: 6px; flex-wrap: wrap; }
.rv-badge { font-size: 11px; padding: 4px 10px; border-radius: 20px; color: var(--accent); background: var(--accent-bg); white-space: nowrap; font-weight: 600; letter-spacing: 0.02em; }
.rv-badge--score { color: #059669; background: #ecfdf5; }
.rv-badge--high { color: #dc2626; background: #fef2f2; }
.rv-badge--medium { color: #d97706; background: #fffbeb; }

.rv-examples { margin-top: 8px; padding-top: 8px; border-top: 1px dashed var(--border); }
.rv-examples-label { font-size: 13px; font-weight: 600; color: var(--text-h); }
.rv-examples-list { margin: 6px 0 0; padding-left: 16px; font-size: 14px; color: var(--text); line-height: 1.7; font-style: italic; border-left: 3px solid var(--accent-light); }

.rv-card--jtbd { gap: 14px; background: linear-gradient(135deg, #fff 0%, #f9fafb 100%); }
.rv-jtbd-title { font-size: 17px; font-weight: 700; margin: 0; color: var(--text-h); }
.rv-jtbd-grid { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 8px 16px; font-size: 14px; }
.rv-jtbd-grid dt { font-weight: 600; color: var(--text-h); white-space: nowrap; }
.rv-jtbd-grid dd { margin: 0; color: var(--text); line-height: 1.6; }

.rv-mvp { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-radius: 10px; padding: 14px 18px; border: 1px solid #a7f3d0; }
.rv-mvp-label { font-size: 13px; font-weight: 700; color: #065f46; }
.rv-mvp-text { margin: 6px 0 0; font-size: 14px; color: #047857; line-height: 1.6; }

.rv-detail-block { margin-top: 12px; }
.rv-detail-label { font-size: 13px; font-weight: 700; color: var(--text-h); display: block; margin-bottom: 6px; }
.rv-detail-list { margin: 0; padding-left: 20px; font-size: 14px; color: var(--text); line-height: 1.7; }
.rv-detail-text { margin: 0; font-size: 14px; color: var(--text); line-height: 1.6; }
.rv-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.rv-tag { font-size: 12px; padding: 5px 12px; border-radius: 20px; background: var(--accent-bg); color: var(--accent); font-weight: 500; }

.rv-badge-ai { font-size: 11px; padding: 3px 10px; border-radius: 20px; background: #fef9c3; color: #854d0e; font-weight: 600; white-space: nowrap; }
.rv-market-data { margin: 8px 0 0; font-size: 14px; color: #1d4ed8; background: #eff6ff; padding: 8px 12px; border-radius: 8px; font-weight: 500; }
.rv-monetization { margin: 8px 0 0; font-size: 14px; color: #059669; font-style: italic; background: #ecfdf5; padding: 8px 12px; border-radius: 8px; }
.rv-empty { text-align: center; color: var(--text); font-size: 15px; padding: 32px; border: 2px dashed var(--border); border-radius: 12px; background: #f9fafb; }
.rv-error { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; border-radius: 12px; padding: 16px 20px; font-size: 14px; }
.rv-error p { margin: 0 0 8px; }

/* Blurred / locked */
.rv-blurred { filter: blur(5px); pointer-events: none; user-select: none; opacity: 0.5; }
.rv-section--locked { opacity: 0.4; }
.rv-lock-badge { font-size: 12px; font-weight: 500; color: var(--text); background: #f3f4f6; padding: 3px 10px; border-radius: 12px; }
.rv-locked-placeholder { text-align: center; padding: 32px; border: 2px dashed var(--border); border-radius: 12px; color: var(--text); font-size: 15px; background: #f9fafb; }

/* Paywall CTA */
.rv-paywall { margin-top: 24px; }
.rv-paywall-inner { text-align: center; padding: 40px 28px; border: 2px solid var(--accent); border-radius: 20px; background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 50%, #fff 100%); box-shadow: 0 8px 32px rgba(0,106,98,0.1); }
.rv-paywall-title { font-size: 26px; margin: 0 0 10px; color: var(--text-h); font-weight: 800; }
.rv-paywall-desc { font-size: 15px; color: var(--text); margin: 0 0 24px; max-width: 500px; margin-left: auto; margin-right: auto; line-height: 1.6; }
.rv-btn--pay { display: inline-flex; align-items: center; justify-content: center; padding: 16px 36px; border: none; border-radius: 12px; background: var(--accent); color: #fff; font-size: 17px; font-weight: 700; cursor: pointer; transition: all 0.2s; box-shadow: 0 4px 12px rgba(0,106,98,0.3); }
.rv-btn--pay:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,106,98,0.4); }
.rv-btn--pay:disabled { opacity: 0.5; cursor: not-allowed; }
.rv-paywall-hint { font-size: 12px; color: var(--text); margin: 14px 0 0; }

.rv-promo { margin-bottom: 20px; }
.rv-promo-row { display: flex; gap: 8px; justify-content: center; max-width: 320px; margin: 0 auto; }
.rv-promo-input { flex: 1; padding: 12px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 14px; outline: none; }
.rv-promo-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,106,98,0.1); }
.rv-promo-btn { padding: 12px 18px; border: none; border-radius: 10px; background: var(--accent-bg); color: var(--accent); font-size: 14px; font-weight: 600; cursor: pointer; }
.rv-promo-btn:hover { background: #d1fae5; }
.rv-promo-success { color: #059669; font-size: 13px; margin: 10px 0 0; font-weight: 500; }
.rv-promo-error { color: #dc2626; font-size: 13px; margin: 10px 0 0; }

.rv-btn { display: inline-flex; align-items: center; padding: 10px 20px; border: none; border-radius: 10px; background: var(--accent); color: #fff; font-size: 14px; cursor: pointer; font-weight: 500; }
.rv-btn--secondary { background: transparent; color: var(--text-h); border: 1px solid var(--border); }

.rv-loading { display: flex; align-items: center; justify-content: center; gap: 10px; padding: 60px; color: var(--text); }
.rv-spinner { width: 24px; height: 24px; border: 3px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: rv-spin 0.6s linear infinite; }
@keyframes rv-spin { to { transform: rotate(360deg); } }

.rv-freq--mass { color: #dc2626; background: #fef2f2; font-weight: 600; }

/* Chat widget */
.rv-chat-context { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 10px; padding: 10px 14px; background: #f0f9ff; border-radius: 10px; border: 1px solid #bae6fd; }
.rv-chat-context-item { font-size: 13px; color: #0369a1; font-weight: 500; }
.rv-chat-hint { font-size: 14px; color: var(--text); margin: 0 0 12px; }
.rv-chat-box { max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; margin-bottom: 12px; padding: 12px; background: #f9fafb; border-radius: 12px; border: 1px solid var(--border); }
.rv-chat-msg { padding: 10px 14px; border-radius: 10px; max-width: 85%; }
.rv-chat-msg--user { align-self: flex-end; background: var(--accent); color: #fff; }
.rv-chat-msg--user .rv-chat-role { color: rgba(255,255,255,0.7); }
.rv-chat-msg--ai { align-self: flex-start; background: #fff; border: 1px solid var(--border); }
.rv-chat-role { font-size: 11px; font-weight: 600; display: block; margin-bottom: 4px; }
.rv-chat-text { margin: 0; font-size: 14px; line-height: 1.5; white-space: pre-wrap; }
.rv-chat-input-row { display: flex; gap: 8px; }
.rv-chat-input { flex: 1; padding: 12px 16px; border: 1px solid var(--border); border-radius: 10px; font-size: 14px; outline: none; }
.rv-chat-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,106,98,0.1); }
.rv-chat-send { padding: 12px 20px; border: none; border-radius: 10px; background: var(--accent); color: #fff; font-size: 18px; font-weight: 700; cursor: pointer; }
.rv-chat-send:disabled { opacity: 0.4; cursor: not-allowed; }
.rv-chat-exhausted { font-size: 13px; color: var(--text); font-style: italic; }
.rv-freq--often { color: #d97706; background: #fffbeb; font-weight: 600; }
.rv-freq--periodic { color: #2563eb; background: #eff6ff; font-weight: 600; }
.rv-freq--rare { color: #6b7280; background: #f3f4f6; }

/* Structured Risks section */
.rv-risks-section { margin-top: 12px; }
.rv-risk-group { margin-top: 14px; padding: 12px 16px; background: #f9fafb; border-radius: 10px; border: 1px solid var(--border); }
.rv-risk-group + .rv-risk-group { margin-top: 10px; }
.rv-risk-category-heading { font-size: 14px; font-weight: 700; color: var(--text-h); margin: 0 0 10px; display: flex; align-items: center; gap: 6px; }
.rv-risk-category-icon { font-size: 16px; }
.rv-risk-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.rv-risk-item { padding: 10px 14px; background: #fff; border-radius: 8px; border: 1px solid #e5e7eb; }
.rv-risk-description { margin: 0 0 6px; font-size: 14px; color: var(--text); line-height: 1.6; }
.rv-risk-mitigation { margin: 0; font-size: 13px; color: #059669; line-height: 1.5; }
.rv-risk-mitigation-label { font-weight: 600; color: #047857; }

/* Recommendations numbered list */
.rv-recommendations-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; counter-reset: none; }
.rv-recommendation-item { display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px; background: #f9fafb; border-radius: 10px; border: 1px solid var(--border); transition: background 0.2s; }
.rv-recommendation-item:hover { background: #f0fdf4; }
.rv-recommendation-number { display: flex; align-items: center; justify-content: center; min-width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 13px; font-weight: 700; flex-shrink: 0; }
.rv-recommendation-text { font-size: 14px; color: var(--text); line-height: 1.6; }
.rv-recommendation-timeframe { font-weight: 700; color: #2563eb; margin-right: 4px; }

/* Two-column pains layout — now handled by Tailwind grid utilities in template */

.rv-mentions-list { display: flex; flex-direction: column; gap: 14px; }
.rv-mention-row { display: flex; align-items: center; gap: 12px; }
.rv-mention-bar-wrap { flex: 1; min-width: 0; }
.rv-mention-label { font-size: 14px; color: var(--text-h); font-weight: 500; margin-bottom: 6px; line-height: 1.4; }
.rv-mention-bar-bg { height: 10px; background: #f3f4f6; border-radius: 5px; overflow: hidden; }
.rv-mention-bar-fill { height: 100%; background: linear-gradient(90deg, var(--accent), #34d399); border-radius: 5px; transition: width 0.5s; }
.rv-mention-count { font-size: 18px; font-weight: 700; color: var(--accent); min-width: 36px; text-align: right; }
</style>
