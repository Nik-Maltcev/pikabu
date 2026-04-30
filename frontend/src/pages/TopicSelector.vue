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

const fingerprint = ref('')
const remainingAnalyses = ref(3)
const limitReached = ref(false)

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

async function onStart() {
  if (!canStart.value) return
  analyzing.value = true
  error.value = ''
  try {
    const topicId = selectedTopic.value!.id
    const res = await startAnalysis(topicId, selectedDays.value, fingerprint.value)
    remainingAnalyses.value = Math.max(0, remainingAnalyses.value - 1)
    if (remainingAnalyses.value <= 0) limitReached.value = true
    router.push({ name: 'analysis', params: { taskId: res.task_id }, query: { topicId: String(topicId) } })
  } catch (e: any) {
    if (e?.response?.status === 429) { limitReached.value = true; remainingAnalyses.value = 0 }
    error.value = e?.response?.data?.detail || e?.message || 'Не удалось запустить анализ'
  } finally { analyzing.value = false }
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
  <div class="bg-[#fcf8fa] text-[#1b1b1d] min-h-screen flex flex-col font-['Inter']">
    <!-- Navbar -->
    <nav class="fixed top-0 w-full z-50 border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div class="flex justify-between items-center px-6 h-16 max-w-7xl mx-auto">
        <div class="flex items-center gap-8">
          <span class="text-xl font-bold tracking-tight text-slate-900">BizNiche AI</span>
          <div class="hidden md:flex gap-6">
            <a class="text-cyan-600 border-b-2 border-cyan-600 pb-1 text-sm font-medium">Поиск ниш</a>
            <a class="text-slate-600 hover:text-slate-900 text-sm font-medium cursor-pointer">Аналитика</a>
            <a class="text-slate-600 hover:text-slate-900 text-sm font-medium cursor-pointer">Мои отчеты</a>
            <a class="text-slate-600 hover:text-slate-900 text-sm font-medium cursor-pointer">Тарифы</a>
          </div>
        </div>
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

      <!-- Limit -->
      <div v-if="limitReached" class="bg-amber-50 text-amber-800 border border-amber-200 rounded-xl px-4 py-3 text-sm">
        🔒 Лимит бесплатных анализов исчерпан. Оплатите для продолжения.
      </div>

      <!-- Action -->
      <div class="flex items-center justify-between">
        <span v-if="!limitReached" class="text-sm text-[#76777d]">
          Бесплатных анализов: <strong class="text-[#006a62]">{{ remainingAnalyses }}</strong>
        </span>
        <span v-else></span>
        <button
          class="bg-black text-white text-base px-8 py-4 rounded-xl flex items-center gap-2 hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
          :disabled="!canStart || analyzing"
          @click="onStart"
        >
          <template v-if="analyzing">
            <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
            Анализируем…
          </template>
          <template v-else>
            Далее
            <span class="material-symbols-outlined text-[20px]">arrow_forward</span>
          </template>
        </button>
      </div>
    </main>

    <!-- Footer -->
    <footer class="w-full mt-auto border-t border-slate-200 bg-slate-50">
      <div class="flex flex-col md:flex-row justify-between items-center py-12 px-6 max-w-7xl mx-auto gap-4">
        <span class="text-xs text-slate-500">© 2025 BizNiche AI. Профессиональная аналитика бизнес-ниш.</span>
        <div class="flex gap-4 flex-wrap justify-center">
          <a class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" href="#">О сервисе</a>
          <a class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" href="#">Методология</a>
          <a class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" href="#">API</a>
          <a class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" href="#">Поддержка</a>
          <a class="text-xs text-slate-500 hover:text-cyan-600 transition-colors" href="#">Конфиденциальность</a>
        </div>
        <span class="font-bold text-slate-900">BizNiche AI</span>
      </div>
    </footer>
  </div>
</template>
