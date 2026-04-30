<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goToApp() {
  router.push({ name: 'topics' })
}
</script>

<template>
  <div class="bg-[#fcf8fa] text-[#1b1b1d] min-h-screen flex flex-col font-['Inter']">
    <!-- Navbar -->
    <nav class="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-200 flex justify-between items-center px-6 h-16">
      <div class="max-w-7xl w-full mx-auto flex justify-between items-center">
        <div class="text-xl font-bold tracking-tight text-slate-900">BizNiche AI</div>
        <div class="hidden md:flex gap-6">
          <a class="text-cyan-600 border-b-2 border-cyan-600 pb-1 text-sm font-medium" href="#">Поиск ниш</a>
          <a class="text-slate-600 hover:text-slate-900 text-sm font-medium" href="#">Аналитика</a>
          <a class="text-slate-600 hover:text-slate-900 text-sm font-medium" href="#">Мои отчеты</a>
          <a class="text-slate-600 hover:text-slate-900 text-sm font-medium" href="#">Тарифы</a>
        </div>
        <button class="bg-black text-white text-xs font-medium px-4 py-2 rounded hover:opacity-80 transition-opacity" @click="goToApp">
          Войти
        </button>
      </div>
    </nav>

    <main class="flex-grow pt-24 pb-16">
      <!-- Hero -->
      <section class="max-w-7xl mx-auto px-6 pt-12 pb-24 text-center">
        <h1 class="text-5xl font-bold tracking-tight leading-tight mb-6 max-w-4xl mx-auto">
          Найдите прибыльную нишу для вашего бизнеса за 5 минут с помощью ИИ
        </h1>
        <p class="text-base text-[#45464d] max-w-2xl mx-auto mb-10 leading-relaxed">
          Мощный алгоритм анализирует тысячи трендов, поисковых запросов и данных конкурентов, чтобы выдать вам готовый план действий.
        </p>
        <button
          class="bg-[#57fae9] text-[#007168] text-xl font-semibold px-8 py-4 rounded-lg hover:opacity-90 transition-opacity shadow-sm"
          @click="goToApp"
        >
          Начать поиск
        </button>

        <!-- Dashboard image -->
        <div class="mt-16 max-w-5xl mx-auto h-96 rounded-xl overflow-hidden border border-[#c6c6cd] relative">
          <img
            alt="Dashboard Preview"
            class="w-full h-full object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuD7epAI-l4-vnIB7hMmU-fwxbAgEB-8y89OIzjzNxaLsX_AtSRf37-yGwCnbKuNQ-kH3ZO_VEotjITvFFy1p9-Y2sD7sZpXJMtXivjla6D5GuHpAFA92XgvuoMeGM8O_uCfuslBud0A9cvDhkv8l7_-7a1QkaQCbd-An8BJmqPc4CSXWO0zR_MUjgBzVxWcVXBU-H6Nm0AkH8F0bgMn-i9OodTHl_igUp3FN52Mmc9iVuv3hxbwRltG05KmqegaQH1PG8rlzPv2m7Y"
          />
          <div class="absolute inset-0 bg-gradient-to-t from-white/20 to-transparent"></div>
        </div>
      </section>

      <!-- How it works -->
      <section class="bg-[#f6f3f5] py-24">
        <div class="max-w-7xl mx-auto px-6">
          <h2 class="text-3xl font-semibold tracking-tight text-center mb-16">Как это работает</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div class="bg-white p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-16 h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-6">
                <span class="material-symbols-outlined text-3xl icon-fill">database</span>
              </div>
              <h3 class="text-xl font-semibold mb-4">Сбор данных</h3>
              <p class="text-sm text-[#45464d] leading-relaxed">
                Мы агрегируем данные из сотен источников: поисковые тренды, соцсети, маркетплейсы и открытые базы данных.
              </p>
            </div>
            <div class="bg-white p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-16 h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-6">
                <span class="material-symbols-outlined text-3xl icon-fill">psychology</span>
              </div>
              <h3 class="text-xl font-semibold mb-4">ИИ-анализ</h3>
              <p class="text-sm text-[#45464d] leading-relaxed">
                Наши нейросети оценивают конкуренцию, потенциальный спрос, маржинальность и риски для каждой ниши.
              </p>
            </div>
            <div class="bg-white p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-16 h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-6">
                <span class="material-symbols-outlined text-3xl icon-fill">description</span>
              </div>
              <h3 class="text-xl font-semibold mb-4">Готовый отчет</h3>
              <p class="text-sm text-[#45464d] leading-relaxed">
                Вы получаете структурированный отчет с рекомендациями, целевой аудиторией и планом запуска.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- Benefits bento grid -->
      <section class="max-w-7xl mx-auto px-6 py-24">
        <h2 class="text-3xl font-semibold tracking-tight mb-12">Преимущества для старта</h2>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 auto-rows-[240px]">
          <!-- Large -->
          <div class="md:col-span-2 md:row-span-2 bg-[#fcf8fa] p-8 border border-[#c6c6cd] rounded-xl flex flex-col justify-between">
            <div>
              <span class="material-symbols-outlined text-4xl text-[#006a62] mb-4">speed</span>
              <h3 class="text-xl font-semibold mb-2">Экономия времени</h3>
              <p class="text-base text-[#45464d] leading-relaxed">
                Вместо недель ручного ресерча вы получаете результат за минуты. Фокусируйтесь на продукте, а не на поиске данных.
              </p>
            </div>
            <div class="mt-4 flex gap-2">
              <span class="bg-[#eae7e9] text-[#45464d] px-3 py-1 rounded-full text-xs font-medium border border-[#c6c6cd]">Быстро</span>
              <span class="bg-[#eae7e9] text-[#45464d] px-3 py-1 rounded-full text-xs font-medium border border-[#c6c6cd]">Точно</span>
            </div>
          </div>
          <!-- Medium -->
          <div class="md:col-span-2 bg-[#fcf8fa] p-8 border border-[#c6c6cd] rounded-xl flex items-center gap-6">
            <span class="material-symbols-outlined text-4xl text-[#006a62] shrink-0">trending_up</span>
            <div>
              <h3 class="text-xl font-semibold mb-2">Снижение рисков</h3>
              <p class="text-sm text-[#45464d]">Объективная оценка на основе данных, а не интуиции.</p>
            </div>
          </div>
          <!-- Small -->
          <div class="bg-[#fcf8fa] p-6 border border-[#c6c6cd] rounded-xl flex flex-col justify-between">
            <span class="material-symbols-outlined text-3xl text-[#006a62]">insights</span>
            <h3 class="text-base font-semibold">Глубокая аналитика</h3>
          </div>
          <div class="bg-[#fcf8fa] p-6 border border-[#c6c6cd] rounded-xl flex flex-col justify-between">
            <span class="material-symbols-outlined text-3xl text-[#006a62]">update</span>
            <h3 class="text-base font-semibold">Свежие тренды</h3>
          </div>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="bg-slate-50 w-full mt-auto border-t border-slate-200 flex flex-col md:flex-row justify-between items-center py-12 px-6 max-w-7xl mx-auto gap-4">
      <div class="font-bold text-slate-900">
        © 2025 BizNiche AI. Профессиональная аналитика бизнес-ниш.
      </div>
      <div class="flex flex-wrap gap-4 text-xs text-slate-500">
        <a class="hover:text-cyan-600 transition-colors" href="#">О сервисе</a>
        <a class="hover:text-cyan-600 transition-colors" href="#">Методология</a>
        <a class="hover:text-cyan-600 transition-colors" href="#">API</a>
        <a class="hover:text-cyan-600 transition-colors" href="#">Поддержка</a>
        <a class="hover:text-cyan-600 transition-colors" href="#">Конфиденциальность</a>
      </div>
    </footer>
  </div>
</template>
