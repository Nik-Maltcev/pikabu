<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getTopics, startAnalysis, checkLimit, createPaidAnalysis, checkPromoCode, login, register, checkAuth } from '../api/client'
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

const fingerprint = ref('')
const remainingAnalyses = ref(3)
const limitReached = ref(false)

// Contact form state
const showContactForm = ref(false)
const contactType = ref<'email' | 'telegram'>('email')
const contactValue = ref('')
const contactError = ref('')
const waitOnPage = ref(false)

// Auth state
const isAuthenticated = ref(false)
const authToken = ref('')
const showAuthModal = ref(false)
const authMode = ref<'login' | 'register'>('login')
const authEmail = ref('')
const authPassword = ref('')
const authError = ref('')
const authLoading = ref(false)

const recommendedTags = ['Маркетинг', 'AI', 'Разработка', 'Еда']

// Featured categories — must match real topic names from the database
const mainCategoriesLarge = [
  { icon: 'shopping_cart', name: 'Маркетплейсы', desc: 'Торговые площадки, интернет-магазины', bg: 'bg-[#dae2fd]', text: 'text-[#131b2e]' },
  { icon: 'code', name: 'Разработка', desc: 'ПО, облачные сервисы, IT', bg: 'bg-[#57fae9]', text: 'text-[#007168]' },
]

const mainCategoriesSmall = [
  { icon: 'campaign', name: 'Маркетинг' },
  { icon: 'restaurant', name: 'Еда' },
  { icon: 'health_and_safety', name: 'Здоровье' },
  { icon: 'savings', name: 'Инвестиции' },
  { icon: 'travel_explore', name: 'Путешествия' },
]

const filteredTopics = computed(() => {
  if (!searchQuery.value) return allTopics.value
  const q = searchQuery.value.toLowerCase()
  return allTopics.value.filter(t => t.name.toLowerCase().includes(q))
})

async function loadTopics() {
  loading.value = true
  error.value = ''
  try {
    const res = await getTopics()
    allTopics.value = res?.topics ?? []
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось загрузить категории'
  } finally {
    loading.value = false
  }
}

function selectByName(name: string) {
  const topic = allTopics.value.find(t => t.name.toLowerCase() === name.toLowerCase())
  if (topic) { selectedTopic.value = topic }
  else { searchQuery.value = name; showAllCategories.value = true }
}

function selectTopic(topic: Topic) {
  selectedTopic.value = topic
  showAllCategories.value = false
}

const canStart = computed(() => selectedTopic.value !== null && !limitReached.value)

function validateContact(): boolean {
  contactError.value = ''
  
  // If authenticated or waiting on page, no contact needed
  if (isAuthenticated.value || waitOnPage.value) {
    return true
  }
  
  const val = contactValue.value.trim()
  
  if (!val) {
    contactError.value = 'Введите контакт для уведомления'
    return false
  }
  
  if (contactType.value === 'email') {
    if (!val.includes('@') || !val.includes('.')) {
      contactError.value = 'Введите корректный email'
      return false
    }
  } else if (contactType.value === 'telegram') {
    const username = val.replace(/^@/, '')
    if (username.length < 3) {
      contactError.value = 'Введите корректный username Telegram'
      return false
    }
  }
  
  return true
}

function onNextClick() {
  if (!canStart.value) return
  // Show auth modal first (user can skip)
  showAuthModal.value = true
}

function onBackToSelection() {
  showContactForm.value = false
  contactError.value = ''
}

// Auth functions
async function onLogin() {
  authError.value = ''
  if (!authEmail.value || !authPassword.value) {
    authError.value = 'Заполните все поля'
    return
  }
  authLoading.value = true
  try {
    const res = await login(authEmail.value, authPassword.value)
    authToken.value = res.token
    isAuthenticated.value = true
    localStorage.setItem('authToken', res.token)
    showAuthModal.value = false
    // Continue to contact form
    showContactForm.value = true
  } catch (e: any) {
    authError.value = e?.response?.data?.detail || 'Ошибка входа'
  } finally {
    authLoading.value = false
  }
}

async function onRegister() {
  authError.value = ''
  if (!authEmail.value || !authPassword.value) {
    authError.value = 'Заполните все поля'
    return
  }
  if (authPassword.value.length < 6) {
    authError.value = 'Пароль минимум 6 символов'
    return
  }
  authLoading.value = true
  try {
    const res = await register(authEmail.value, authPassword.value)
    authToken.value = res.token
    isAuthenticated.value = true
    localStorage.setItem('authToken', res.token)
    showAuthModal.value = false
    // Continue to contact form
    showContactForm.value = true
  } catch (e: any) {
    authError.value = e?.response?.data?.detail || 'Ошибка регистрации'
  } finally {
    authLoading.value = false
  }
}

function onLogout() {
  authToken.value = ''
  isAuthenticated.value = false
  localStorage.removeItem('authToken')
}

function onSkipAuth() {
  showAuthModal.value = false
  showContactForm.value = true
}

async function onStart() {
  if (!canStart.value) return
  if (!validateContact()) return
  
  analyzing.value = true
  error.value = ''
  try {
    const topicId = selectedTopic.value!.id
    const contact = contactType.value === 'telegram' 
      ? contactValue.value.trim().replace(/^@/, '') 
      : contactValue.value.trim()
    
    const res = await startAnalysis(
      topicId, 
      selectedDays.value, 
      fingerprint.value, 
      waitOnPage.value ? '' : contactType.value, 
      waitOnPage.value ? '' : contact,
      waitOnPage.value,
      authToken.value || undefined
    )
    remainingAnalyses.value = Math.max(0, remainingAnalyses.value - 1)
    if (remainingAnalyses.value <= 0) limitReached.value = true
    router.push({ name: 'analysis', params: { taskId: res.task_id }, query: { topicId: String(topicId) } })
  } catch (e: any) {
    if (e?.response?.status === 429) { limitReached.value = true; remainingAnalyses.value = 0 }
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось запустить анализ'
  } finally { analyzing.value = false }
}

const paymentLoading = ref(false)
const waitingPayment = ref(false)
let paymentPollTimer: ReturnType<typeof setInterval> | null = null

const paidPromoCode = ref('')
const paidPromoApplied = ref(false)
const paidPromoPrice = ref(0)
const paidPromoDiscount = ref(0)
const paidPromoError = ref('')

async function onApplyPaidPromo() {
  paidPromoError.value = ''
  if (!paidPromoCode.value.trim()) return
  try {
    const res = await checkPromoCode(paidPromoCode.value.trim())
    if (res.valid) {
      paidPromoApplied.value = true
      paidPromoPrice.value = res.price!
      paidPromoDiscount.value = res.discount_percent!
    } else {
      paidPromoError.value = 'Промокод не найден'
      paidPromoApplied.value = false
    }
  } catch {
    paidPromoError.value = 'Ошибка проверки'
  }
}

async function onPaidStart() {
  if (!selectedTopic.value) return
  paymentLoading.value = true
  error.value = ''
  try {
    const code = paidPromoApplied.value ? paidPromoCode.value.trim() : undefined
    const result = await createPaidAnalysis(selectedTopic.value.id, selectedDays.value, fingerprint.value, code)
    // Open Robokassa in new window
    window.open(result.payment_url, '_blank')
    // Start polling payment status
    waitingPayment.value = true
    paymentLoading.value = false
    const invId = result.payment_url.match(/InvId=(\d+)/)?.[1]
    if (invId) {
      paymentPollTimer = setInterval(async () => {
        try {
          const apiBase = import.meta.env.VITE_API_URL || '/api'
          const res = await fetch(`${apiBase}/payment/status/${invId}`)
          const data = await res.json()
          if (data.paid && data.task_id) {
            clearInterval(paymentPollTimer!)
            paymentPollTimer = null
            waitingPayment.value = false
            router.push({ name: 'analysis', params: { taskId: data.task_id }, query: { topicId: String(data.topic_id || selectedTopic.value?.id) } })
          }
        } catch {}
      }, 3000)
    }
  } catch (e: any) {
    error.value = e?.response?.data?.detail || e?.message || 'Ошибка создания платежа'
    paymentLoading.value = false
  }
}

onMounted(async () => {
  fingerprint.value = await generateFingerprint()
  
  // Check saved auth token
  const savedToken = localStorage.getItem('authToken')
  if (savedToken) {
    try {
      const authCheck = await checkAuth(savedToken)
      if (authCheck.authenticated) {
        authToken.value = savedToken
        isAuthenticated.value = true
      } else {
        localStorage.removeItem('authToken')
      }
    } catch {
      localStorage.removeItem('authToken')
    }
  }
  
  try {
    const limit = await checkLimit(fingerprint.value)
    remainingAnalyses.value = limit.remaining
    limitReached.value = limit.remaining <= 0
  } catch {}
  loadTopics()
})
</script>

<template>
  <div class="bg-[#fcf8fa] text-[#1b1b1d] min-h-screen flex flex-col font-['Inter']">
    <!-- Navbar -->
    <nav class="fixed top-0 w-full z-50 border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div class="flex justify-between items-center px-4 h-[60px] max-w-7xl mx-auto">
        <div class="flex items-center gap-5">
          <router-link to="/" class="text-[22px] font-bold tracking-tight text-slate-900 no-underline">BizMap</router-link>
          <div class="flex gap-4">
            <a class="text-cyan-600 border-b-2 border-cyan-600 pb-0.5 text-[18px] font-medium">Ниши</a>
            <router-link to="/account" class="text-slate-600 hover:text-slate-900 text-[18px] font-medium cursor-pointer">Отчеты</router-link>
            <router-link to="/#pricing" class="text-slate-600 hover:text-slate-900 text-[18px] font-medium cursor-pointer">Цены</router-link>
          </div>
        </div>
        <router-link to="/account" class="bg-black text-white text-[16px] font-medium px-4 py-2 rounded-lg hover:opacity-80 transition-opacity no-underline">Войти</router-link>
      </div>
    </nav>

    <!-- Main -->
    <main class="flex-grow pt-24 pb-12 px-6 max-w-[1024px] mx-auto w-full flex flex-col gap-8">

      <!-- Search block -->
      <div class="bg-[#f0edef] rounded-xl p-8 border border-[#c6c6cd]">
        <h1 class="text-[30px] leading-[38px] font-semibold tracking-tight text-[#1b1b1d] mb-2">Выберите категорию бизнеса</h1>
        <p class="text-base text-[#45464d] mb-6">Укажите сферу, чтобы ИИ смог подобрать наиболее релевантные данные и тренды.</p>

        <div class="relative mb-6">
          <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-[#45464d]">search</span>
          <input
            v-model="searchQuery"
            type="text"
            class="w-full bg-[#fcf8fa] border border-[#c6c6cd] rounded-lg py-4 pl-12 pr-4 text-base text-[#1b1b1d] focus:outline-none focus:ring-2 focus:ring-[#006a62] focus:border-transparent transition-shadow"
            placeholder="Поиск категорий (например, Кофейня, SaaS...)"
            @focus="showAllCategories = true"
          />
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <span class="text-xs font-medium text-[#45464d] uppercase tracking-wider flex items-center gap-1">
            <span class="material-symbols-outlined text-[16px]">psychology</span> ИИ рекомендует:
          </span>
          <button
            v-for="tag in recommendedTags"
            :key="tag"
            class="bg-[#fcf8fa] rounded-full px-4 py-2 text-xs font-medium text-[#1b1b1d] border border-[#c6c6cd] hover:border-[#006a62] hover:text-[#006a62] transition-colors"
            :class="{ '!bg-[#006a62] !text-white !border-[#006a62]': selectedTopic?.name === tag }"
            @click="selectByName(tag)"
          >{{ tag }}</button>
        </div>
      </div>

      <!-- Category grid -->
      <div v-if="!showAllCategories" class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <!-- Large cards -->
        <button
          v-for="cat in mainCategoriesLarge"
          :key="cat.name"
          class="col-span-2 bg-[#fcf8fa] border border-[#c6c6cd] rounded-xl p-6 flex flex-col items-start justify-between h-40 hover:border-black hover:bg-[#f6f3f5] transition-colors group text-left"
          :class="{ '!border-black !bg-[#f6f3f5]': selectedTopic?.name === cat.name }"
          @click="selectByName(cat.name)"
        >
          <div :class="[cat.bg, cat.text, 'p-3 rounded-lg w-fit']">
            <span class="material-symbols-outlined text-[28px]">{{ cat.icon }}</span>
          </div>
          <div>
            <h3 class="text-xl font-semibold text-[#1b1b1d] group-hover:text-black">{{ cat.name }}</h3>
            <p class="text-sm text-[#45464d] mt-1">{{ cat.desc }}</p>
          </div>
        </button>

        <!-- Small cards -->
        <button
          v-for="cat in mainCategoriesSmall"
          :key="cat.name"
          class="bg-[#fcf8fa] border border-[#c6c6cd] rounded-xl p-6 flex flex-col items-center justify-center gap-4 h-32 hover:border-black hover:bg-[#f6f3f5] transition-colors group"
          :class="{ '!border-black !bg-[#f6f3f5]': selectedTopic?.name === cat.name }"
          @click="selectByName(cat.name)"
        >
          <span class="material-symbols-outlined text-[32px] text-[#45464d] group-hover:text-black transition-colors">{{ cat.icon }}</span>
          <span class="text-xs font-medium text-[#1b1b1d] text-center">{{ cat.name }}</span>
        </button>

        <!-- All categories -->
        <button
          class="bg-[#f6f3f5] border border-[#c6c6cd] rounded-xl p-6 flex flex-col items-center justify-center gap-4 h-32 hover:border-black transition-colors group"
          @click="showAllCategories = true"
        >
          <span class="material-symbols-outlined text-[32px] text-[#45464d] group-hover:text-black transition-colors">apps</span>
          <span class="text-xs font-medium text-[#1b1b1d] text-center">Все категории</span>
        </button>
      </div>

      <!-- Full list -->
      <div v-if="showAllCategories">
        <div v-if="loading" class="flex items-center justify-center gap-3 py-10 text-[#76777d]">
          <div class="w-5 h-5 border-2 border-[#c6c6cd] border-t-[#006a62] rounded-full animate-spin"></div>
          Загрузка…
        </div>
        <ul v-else class="max-h-80 overflow-y-auto bg-[#fcf8fa] border border-[#c6c6cd] rounded-xl divide-y divide-[#e4e2e4]">
          <li
            v-for="topic in filteredTopics"
            :key="topic.id"
            class="px-5 py-3.5 cursor-pointer text-sm hover:bg-[#f6f3f5] transition-colors"
            :class="{ 'bg-[#f0fdf9] text-[#006a62] font-medium': selectedTopic?.id === topic.id }"
            @click="selectTopic(topic)"
          >{{ topic.name }}</li>
          <li v-if="filteredTopics.length === 0" class="px-5 py-8 text-center text-sm text-[#76777d]">Категории не найдены</li>
        </ul>
        <button class="mt-3 text-sm text-[#76777d] hover:text-[#006a62] transition-colors" @click="showAllCategories = false">← Назад к основным</button>
      </div>

      <!-- Selection bar -->
      <div v-if="selectedTopic" class="flex items-center justify-between p-4 bg-[#f0fdf9] border border-[#d1fae5] rounded-xl flex-wrap gap-3">
        <div class="flex items-center gap-2">
          <span class="text-sm text-[#45464d]">Выбрано:</span>
          <span class="text-sm font-semibold">{{ selectedTopic.name }}</span>
        </div>
        <div class="flex gap-2">
          <button
            class="px-4 py-2 border rounded-lg text-sm transition-all"
            :class="selectedDays === 14 ? 'bg-black text-white border-black' : 'bg-[#fcf8fa] text-[#1b1b1d] border-[#c6c6cd] hover:border-black'"
            @click="selectedDays = 14"
          >14 дней</button>
          <button
            class="px-4 py-2 border rounded-lg text-sm transition-all flex items-center gap-1.5"
            :class="selectedDays === 30 ? 'bg-black text-white border-black' : 'bg-[#fcf8fa] text-[#1b1b1d] border-[#c6c6cd] hover:border-black'"
            @click="selectedDays = 30"
          >30 дней <span class="w-4 h-4 bg-[#006a62] text-white text-[9px] font-bold rounded-full inline-flex items-center justify-center">₽</span></button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="bg-red-50 text-red-700 border border-red-200 rounded-xl px-4 py-3 text-sm">{{ error }}</div>

      <!-- Waiting for payment -->
      <div v-if="waitingPayment" class="bg-blue-50 text-blue-800 border border-blue-200 rounded-xl px-5 py-4 text-sm text-center">
        <div class="w-5 h-5 border-2 border-blue-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-3"></div>
        <p class="font-semibold mb-1">⏳ Ожидаем подтверждение оплаты...</p>
        <p>Завершите оплату в открывшемся окне. Страница обновится автоматически.</p>
      </div>

      <!-- Limit -->
      <div v-else-if="limitReached && selectedTopic" class="bg-amber-50 text-amber-800 border border-amber-200 rounded-xl px-5 py-4 text-sm">
        <p class="font-semibold mb-1">🔒 Бесплатные анализы исчерпаны</p>
        <p class="mb-3">Оплатите — после оплаты анализ запустится автоматически и вы получите полный отчёт.</p>
        <!-- Promo code -->
        <div class="flex gap-2 mb-3">
          <input v-model="paidPromoCode" type="text" placeholder="Промокод" class="flex-1 px-3 py-2 border border-amber-300 rounded-lg text-sm bg-white" @keyup.enter="onApplyPaidPromo" />
          <button class="px-4 py-2 bg-[#006a62] text-white rounded-lg text-sm font-medium hover:bg-[#005a54] transition-colors" @click="onApplyPaidPromo">Применить</button>
        </div>
        <p v-if="paidPromoApplied" class="text-green-700 text-xs mb-2">✓ Скидка {{ paidPromoDiscount }}% — цена {{ paidPromoPrice.toLocaleString() }} ₽</p>
        <p v-if="paidPromoError" class="text-red-700 text-xs mb-2">{{ paidPromoError }}</p>
        <button
          class="bg-[#006a62] text-white text-sm font-medium px-6 py-3 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
          :disabled="paymentLoading"
          @click="onPaidStart"
        >
          {{ paymentLoading ? 'Переход к оплате...' : paidPromoApplied ? `Оплатить ${paidPromoPrice.toLocaleString()} ₽` : 'Оплатить и запустить анализ — 4 990 ₽' }}
        </button>
      </div>
      <div v-else-if="limitReached && !selectedTopic" class="bg-amber-50 text-amber-800 border border-amber-200 rounded-xl px-4 py-3 text-sm">
        🔒 Бесплатные анализы исчерпаны. Выберите категорию и оплатите для продолжения.
      </div>

      <!-- Action -->
      <div class="flex items-center justify-between">
        <span v-if="!limitReached" class="text-sm text-[#76777d]">
          Бесплатных анализов: <strong class="text-[#006a62]">{{ remainingAnalyses }}</strong>
        </span>
        <span v-else></span>
        <button
          v-if="!limitReached && !showContactForm"
          class="bg-black text-white text-base px-8 py-4 rounded-xl flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="!canStart || analyzing"
          @click="onNextClick"
        >
          Далее
          <span class="material-symbols-outlined text-[20px]">arrow_forward</span>
        </button>
      </div>

      <!-- Auth Modal -->
      <div v-if="showAuthModal && !limitReached" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl p-6 w-full max-w-md shadow-xl">
          <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-semibold text-[#1b1b1d]">
              {{ authMode === 'login' ? 'Вход в аккаунт' : 'Регистрация' }}
            </h2>
            <button @click="showAuthModal = false" class="text-[#76777d] hover:text-[#1b1b1d]">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>

          <p class="text-sm text-[#45464d] mb-6">
            {{ authMode === 'login' ? 'Войдите, чтобы сохранять отчёты в личном кабинете' : 'Создайте аккаунт для сохранения отчётов' }}
          </p>

          <div class="space-y-4 mb-4">
            <input
              v-model="authEmail"
              type="email"
              placeholder="Email"
              class="w-full bg-[#fcf8fa] border border-[#c6c6cd] rounded-lg py-3 px-4 text-base focus:outline-none focus:ring-2 focus:ring-[#006a62]"
              @keyup.enter="authMode === 'login' ? onLogin() : onRegister()"
            />
            <input
              v-model="authPassword"
              type="password"
              placeholder="Пароль"
              class="w-full bg-[#fcf8fa] border border-[#c6c6cd] rounded-lg py-3 px-4 text-base focus:outline-none focus:ring-2 focus:ring-[#006a62]"
              @keyup.enter="authMode === 'login' ? onLogin() : onRegister()"
            />
          </div>

          <p v-if="authError" class="text-red-600 text-sm mb-4">{{ authError }}</p>

          <div class="flex gap-3 mb-4">
            <button
              class="flex-1 bg-black text-white py-3 px-4 rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-30"
              :disabled="authLoading"
              @click="authMode === 'login' ? onLogin() : onRegister()"
            >
              {{ authLoading ? 'Загрузка...' : (authMode === 'login' ? 'Войти' : 'Создать аккаунт') }}
            </button>
          </div>

          <div class="text-center text-sm text-[#45464d] mb-4">
            <span v-if="authMode === 'login'">
              Нет аккаунта? 
              <button class="text-[#006a62] hover:underline" @click="authMode = 'register'; authError = ''">Зарегистрироваться</button>
            </span>
            <span v-else>
              Уже есть аккаунт? 
              <button class="text-[#006a62] hover:underline" @click="authMode = 'login'; authError = ''">Войти</button>
            </span>
          </div>

          <div class="border-t border-[#e4e2e4] pt-4">
            <button
              class="w-full py-3 px-4 rounded-lg border border-[#c6c6cd] text-sm font-medium text-[#45464d] hover:border-[#1b1b1d] hover:text-[#1b1b1d]"
              @click="onSkipAuth"
            >
              Продолжить без регистрации →
            </button>
          </div>
        </div>
      </div>

      <!-- Contact Form Modal -->
      <div v-if="showContactForm && !limitReached && !showAuthModal" class="bg-white border border-[#c6c6cd] rounded-xl p-6 shadow-lg">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-semibold text-[#1b1b1d]">
            {{ isAuthenticated ? 'Запуск анализа' : 'Куда отправить результат?' }}
          </h2>
          <button @click="onBackToSelection" class="text-[#76777d] hover:text-[#1b1b1d] transition-colors">
            <span class="material-symbols-outlined">close</span>
          </button>
        </div>
        
        <!-- Authenticated user info -->
        <div v-if="isAuthenticated" class="bg-[#f0fdf9] border border-[#d1fae5] rounded-lg p-4 mb-6">
          <div class="flex items-center gap-2 text-sm text-[#006a62]">
            <span class="material-symbols-outlined text-[20px]">check_circle</span>
            <span>Вы авторизованы. Отчёт сохранится в личном кабинете.</span>
          </div>
        </div>

        <!-- Guest options -->
        <div v-else>
          <p class="text-sm text-[#45464d] mb-4">Анализ занимает 5-10 минут. Выберите как получить результат:</p>

          <!-- Wait on page option -->
          <label class="flex items-center gap-3 p-4 border rounded-lg mb-3 cursor-pointer transition-colors"
            :class="waitOnPage ? 'border-[#006a62] bg-[#f0fdf9]' : 'border-[#c6c6cd] hover:border-[#006a62]'"
          >
            <input type="radio" v-model="waitOnPage" :value="true" class="w-4 h-4 text-[#006a62]" />
            <div>
              <div class="text-sm font-medium text-[#1b1b1d]">Подождать на странице</div>
              <div class="text-xs text-[#76777d]">Результат появится здесь через 5-10 минут</div>
            </div>
          </label>

          <!-- Send notification option -->
          <label class="flex items-center gap-3 p-4 border rounded-lg mb-4 cursor-pointer transition-colors"
            :class="!waitOnPage ? 'border-[#006a62] bg-[#f0fdf9]' : 'border-[#c6c6cd] hover:border-[#006a62]'"
          >
            <input type="radio" v-model="waitOnPage" :value="false" class="w-4 h-4 text-[#006a62]" />
            <div>
              <div class="text-sm font-medium text-[#1b1b1d]">Отправить уведомление</div>
              <div class="text-xs text-[#76777d]">Пришлём ссылку на готовый отчёт</div>
            </div>
          </label>

          <!-- Contact input (only if not waiting) -->
          <div v-if="!waitOnPage" class="mb-4">
            <div class="flex gap-3 mb-3">
              <button
                class="flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all flex items-center justify-center gap-2"
                :class="contactType === 'email' ? 'bg-[#006a62] text-white border-[#006a62]' : 'bg-[#fcf8fa] text-[#1b1b1d] border-[#c6c6cd]'"
                @click="contactType = 'email'"
              >
                <span class="material-symbols-outlined text-[18px]">mail</span>
                Email
              </button>
              <button
                class="flex-1 py-2 px-3 rounded-lg border text-sm font-medium transition-all flex items-center justify-center gap-2"
                :class="contactType === 'telegram' ? 'bg-[#006a62] text-white border-[#006a62]' : 'bg-[#fcf8fa] text-[#1b1b1d] border-[#c6c6cd]'"
                @click="contactType = 'telegram'"
              >
                <span class="material-symbols-outlined text-[18px]">send</span>
                Telegram
              </button>
            </div>
            <input
              v-model="contactValue"
              type="text"
              class="w-full bg-[#fcf8fa] border border-[#c6c6cd] rounded-lg py-3 px-4 text-base focus:outline-none focus:ring-2 focus:ring-[#006a62]"
              :placeholder="contactType === 'email' ? 'your@email.com' : '@username'"
            />
            <p v-if="contactError" class="text-red-600 text-sm mt-2">{{ contactError }}</p>
          </div>
        </div>

        <!-- Summary -->
        <div class="bg-[#f6f3f5] rounded-lg p-4 mb-6">
          <div class="flex items-center justify-between text-sm">
            <span class="text-[#45464d]">Категория:</span>
            <span class="font-medium text-[#1b1b1d]">{{ selectedTopic?.name }}</span>
          </div>
          <div class="flex items-center justify-between text-sm mt-2">
            <span class="text-[#45464d]">Период:</span>
            <span class="font-medium text-[#1b1b1d]">{{ selectedDays }} дней</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3">
          <button
            class="flex-1 py-3 px-4 rounded-lg border border-[#c6c6cd] text-sm font-medium text-[#45464d] hover:border-[#1b1b1d] hover:text-[#1b1b1d] transition-colors"
            @click="onBackToSelection"
          >
            Назад
          </button>
          <button
            class="flex-1 bg-black text-white py-3 px-4 rounded-lg text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            :disabled="analyzing"
            @click="onStart"
          >
            <template v-if="analyzing">
              <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              Запускаем…
            </template>
            <template v-else>
              Запустить анализ
              <span class="material-symbols-outlined text-[18px]">rocket_launch</span>
            </template>
          </button>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="w-full mt-auto border-t border-slate-200 bg-slate-50 py-12 px-6">
      <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start gap-8">
        <div>
          <div class="font-bold text-slate-900 text-lg mb-2">BizMap</div>
          <p class="text-xs text-slate-500">© 2025 BizMap. Аналитика бизнес-ниш.</p>
        </div>
        <div class="flex flex-wrap gap-8">
          <div>
            <div class="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">Документы</div>
            <div class="flex flex-col gap-1">
              <router-link class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" to="/pricing">Услуги и цены</router-link>
              <router-link class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" to="/terms">Оферта</router-link>
              <router-link class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" to="/privacy">Конфиденциальность</router-link>
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">Контактная информация</div>
            <div class="flex flex-col gap-1 text-xs text-slate-500">
              <span>Самозанятый Мальцев Н.Е., ИНН 165924805367</span>
              <span>Тел: +7 900 324-21-25</span>
              <span>Email: nikmaltcev@vk.com</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>
