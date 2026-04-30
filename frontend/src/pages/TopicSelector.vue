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

const recommendedTags = ['FinTech', 'EdTech', 'Доставка еды', 'Pet-tech']

const mainCategories = [
  { icon: 'storefront', name: 'Маркетплейсы', desc: 'Маркетплейсы, интернет-магазины' },
  { icon: 'code', name: 'IT', desc: 'Разработка ПО, облачные сервисы' },
  { icon: 'home_repair_service', name: 'Сервис', desc: 'Услуги для бизнеса и людей' },
  { icon: 'factory', name: 'Бизнес', desc: 'Предпринимательство, стартапы' },
  { icon: 'restaurant', name: 'Еда', desc: 'Доставка, рестораны, HoReCa' },
  { icon: 'health_and_safety', name: 'Здоровье', desc: 'Медицина, wellness, фитнес' },
  { icon: 'real_estate_agent', name: 'Инвестиции', desc: 'Финансы, недвижимость' },
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
  <div class="bg-[#fcf8fa] text-[#1b1b1d] min-h-screen flex flex-col font-['Inter']">
    <!-- Navbar -->
    <nav class="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center px-6 h-16">
      <div class="max-w-7xl w-full mx-auto flex justify-between items-center">
        <div class="text-xl font-bold tracking-tight text-slate-900">BizNiche AI</div>
        <div class="hidden md:flex gap-6">
          <a class="text-cyan-600 border-b-2 border-cyan-600 pb-1 text-sm font-medium">Поиск ниш</a>
          <a class="text-slate-600 hover:text-slate-900 text-sm font-medium cursor-pointer">Аналитика</a>
          <a class="text-slate-600 hover:text-slate-900 text-sm font-medium cursor-pointer">Мои отчеты</a>
          <a class="text-slate-600 hover:text-slate-900 text-sm font-medium cursor-pointer">Тарифы</a>
        </div>
        <button class="bg-black text-white text-xs font-medium px-4 py-2 rounded hover:opacity-80 transition-opacity">
          Войти
        </button>
      </div>
    </nav>

    <!-- Main -->
    <main class="flex-grow pt-24 pb-16">
      <div class="max-w-[900px] mx-auto px-6">
        <div class="bg-white rounded-xl border border-[#c6c6cd] p-10">
          <h1 class="text-3xl font-bold tracking-tight mb-2">Выберите категорию бизнеса</h1>
          <p class="text-[#45464d] text-base mb-8">Укажите сферу, чтобы ИИ смог подобрать наиболее релевантные данные и тренды.</p>

          <!-- Search -->
          <div class="relative mb-4">
            <span class="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-[#76777d] text-xl">search</span>
            <input
              v-model="searchQuery"
              type="text"
              class="w-full pl-12 pr-4 py-3.5 border border-[#c6c6cd] rounded-xl text-base bg-[#f6f3f5] focus:bg-white focus:border-cyan-600 outline-none transition-colors"
              placeholder="Поиск категорий (например, Кофейня, SaaS...)"
              @focus="showAllCategories = true"
            />
          </div>

          <!-- Recommended tags -->
          <div class="flex items-center gap-2 mb-8 flex-wrap">
            <span class="text-xs text-[#76777d] uppercase tracking-wider font-medium whitespace-nowrap">✨ ИИ РЕКОМЕНДУЕТ:</span>
            <button
              v-for="tag in recommendedTags"
              :key="tag"
              class="px-3.5 py-1.5 border border-[#c6c6cd] rounded-full text-sm text-[#1b1b1d] bg-white hover:border-cyan-600 hover:text-cyan-700 transition-colors"
              :class="{ '!bg-cyan-600 !text-white !border-cyan-600': selectedTopic?.name === tag }"
              @click="selectByName(tag)"
            >{{ tag }}</button>
          </div>

          <!-- Category cards -->
          <div v-if="!showAllCategories" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <!-- First two large -->
            <button
              v-for="cat in mainCategories.slice(0, 2)"
              :key="cat.name"
              class="col-span-2 flex items-center gap-4 p-5 border border-[#e4e2e4] rounded-xl bg-white hover:border-cyan-600 hover:shadow-sm transition-all text-left"
              :class="{ '!border-cyan-600 !bg-cyan-50': selectedTopic?.name === cat.name }"
              @click="selectByName(cat.name)"
            >
              <div class="w-12 h-12 bg-[#dae2fd] rounded-xl flex items-center justify-center shrink-0">
                <span class="material-symbols-outlined text-2xl text-[#3f465c]">{{ cat.icon }}</span>
              </div>
              <div>
                <div class="font-semibold text-sm">{{ cat.name }}</div>
                <div class="text-xs text-[#76777d]">{{ cat.desc }}</div>
              </div>
            </button>

            <!-- Rest smaller -->
            <button
              v-for="cat in mainCategories.slice(2)"
              :key="cat.name"
              class="flex flex-col items-center justify-center gap-2 p-5 border border-[#e4e2e4] rounded-xl bg-white hover:border-cyan-600 hover:shadow-sm transition-all text-center"
              :class="{ '!border-cyan-600 !bg-cyan-50': selectedTopic?.name === cat.name }"
              @click="selectByName(cat.name)"
            >
              <span class="material-symbols-outlined text-2xl text-[#45464d]">{{ cat.icon }}</span>
              <span class="text-sm font-medium">{{ cat.name }}</span>
            </button>

            <!-- All categories -->
            <button
              class="flex flex-col items-center justify-center gap-2 p-5 border border-dashed border-[#c6c6cd] rounded-xl bg-white hover:border-cyan-600 transition-all text-center"
              @click="showAllCategories = true"
            >
              <span class="material-symbols-outlined text-2xl text-[#45464d]">apps</span>
              <span class="text-sm font-medium">Все категории</span>
            </button>
          </div>

          <!-- Full list -->
          <div v-if="showAllCategories" class="mb-6">
            <div v-if="loading" class="flex items-center justify-center gap-3 py-10 text-[#76777d]">
              <div class="w-5 h-5 border-2 border-[#c6c6cd] border-t-cyan-600 rounded-full animate-spin"></div>
              Загрузка…
            </div>
            <ul v-else class="max-h-72 overflow-y-auto border border-[#e4e2e4] rounded-xl divide-y divide-[#f6f3f5]">
              <li
                v-for="topic in filteredTopics"
                :key="topic.id"
                class="px-4 py-3 cursor-pointer text-sm hover:bg-cyan-50 transition-colors"
                :class="{ 'bg-cyan-50 text-cyan-700 font-medium': selectedTopic?.id === topic.id }"
                @click="selectTopic(topic)"
              >{{ topic.name }}</li>
              <li v-if="filteredTopics.length === 0" class="px-4 py-6 text-center text-sm text-[#76777d]">
                Категории не найдены
              </li>
            </ul>
            <button class="mt-3 text-sm text-[#76777d] hover:text-cyan-600 transition-colors" @click="showAllCategories = false">
              ← Назад к основным
            </button>
          </div>

          <!-- Selection + Period -->
          <div v-if="selectedTopic" class="flex items-center justify-between p-4 bg-[#f0fdf9] border border-[#d1fae5] rounded-xl mb-4 flex-wrap gap-3">
            <div class="flex items-center gap-2">
              <span class="text-sm text-[#45464d]">Выбрано:</span>
              <span class="text-sm font-semibold">{{ selectedTopic.name }}</span>
            </div>
            <div class="flex gap-2">
              <button
                class="px-4 py-2 border border-[#e4e2e4] rounded-lg text-sm transition-all"
                :class="selectedDays === 14 ? 'bg-black text-white border-black' : 'bg-white text-[#1b1b1d] hover:border-cyan-600'"
                @click="selectedDays = 14"
              >14 дней</button>
              <button
                class="px-4 py-2 border border-[#e4e2e4] rounded-lg text-sm transition-all flex items-center gap-1"
                :class="selectedDays === 30 ? 'bg-black text-white border-black' : 'bg-white text-[#1b1b1d] hover:border-cyan-600'"
                @click="selectedDays = 30"
              >30 дней <span class="w-4 h-4 bg-cyan-600 text-white text-[9px] font-bold rounded-full flex items-center justify-center">₽</span></button>
            </div>
          </div>

          <!-- Error -->
          <div v-if="error" class="bg-red-50 text-red-700 border border-red-200 rounded-xl px-4 py-3 text-sm mb-4">{{ error }}</div>

          <!-- Limit -->
          <div v-if="limitReached" class="bg-amber-50 text-amber-800 border border-amber-200 rounded-xl px-4 py-3 text-sm mb-4">
            🔒 Лимит бесплатных анализов исчерпан. Оплатите для продолжения.
          </div>

          <!-- Action -->
          <div class="flex items-center justify-between">
            <span v-if="!limitReached" class="text-sm text-[#76777d]">
              Бесплатных анализов: <strong class="text-cyan-600">{{ remainingAnalyses }}</strong>
            </span>
            <span v-else></span>
            <button
              class="bg-black text-white text-sm font-medium px-8 py-3.5 rounded-xl hover:opacity-85 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
              :disabled="!canStart || analyzing"
              @click="onStart"
            >
              <template v-if="analyzing">
                <div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                Анализируем…
              </template>
              <template v-else>
                Далее <span class="text-lg">→</span>
              </template>
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="bg-slate-50 w-full mt-auto border-t border-slate-200 py-8 px-6">
      <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
        <div class="text-sm font-bold text-slate-900">© 2025 BizNiche AI. Профессиональная аналитика бизнес-ниш.</div>
        <div class="flex flex-wrap gap-4 text-xs text-slate-500">
          <a class="hover:text-cyan-600 transition-colors" href="#">О сервисе</a>
          <a class="hover:text-cyan-600 transition-colors" href="#">Методология</a>
          <a class="hover:text-cyan-600 transition-colors" href="#">Поддержка</a>
          <a class="hover:text-cyan-600 transition-colors" href="#">Конфиденциальность</a>
        </div>
        <div class="text-sm font-bold text-slate-900">BizNiche AI</div>
      </div>
    </footer>
  </div>
</template>
