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
        <div class="text-xl font-bold tracking-tight text-slate-900">BizMap</div>
        <div class="hidden md:flex gap-6">
          <router-link to="/app" class="text-cyan-600 border-b-2 border-cyan-600 pb-1 text-sm font-medium">Поиск ниш</router-link>
          <router-link to="/account" class="text-slate-600 hover:text-slate-900 text-sm font-medium">Мои отчеты</router-link>
          <router-link to="/pricing" class="text-slate-600 hover:text-slate-900 text-sm font-medium">Тарифы</router-link>
        </div>
        <router-link to="/account" class="bg-black text-white text-xs font-medium px-4 py-2 rounded-lg hover:opacity-80 transition-opacity no-underline">Войти</router-link>
      </div>
    </nav>

    <main class="flex-grow pt-24 pb-16">
      <!-- Hero -->
      <section class="max-w-7xl mx-auto px-6 pt-12 pb-24">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <!-- Left: Text -->
          <div class="text-left">
            <div class="inline-flex items-center gap-2 bg-[#006a62]/10 text-[#006a62] px-4 py-2 rounded-full text-sm font-medium mb-6">
              <span class="material-symbols-outlined text-lg">verified</span>
              Аналитика на основе реальных данных
            </div>
            <h1 class="text-4xl lg:text-5xl font-bold tracking-tight leading-tight mb-6">
              Найдите прибыльную нишу для бизнеса за 5 минут
            </h1>
            <p class="text-lg text-[#45464d] mb-8 leading-relaxed">
              ИИ-платформа анализирует тысячи обсуждений на Pikabu, Habr и VC.ru, выявляет боли аудитории и генерирует готовые бизнес-идеи с планом запуска.
            </p>
            <div class="flex flex-col sm:flex-row gap-4 mb-8">
              <button
                class="bg-[#006a62] text-white text-lg font-semibold px-8 py-4 rounded-lg hover:bg-[#005a54] transition-colors shadow-lg"
                @click="goToApp"
              >
                Начать анализ бесплатно
              </button>
              <a href="#partners" class="border-2 border-[#006a62] text-[#006a62] text-lg font-semibold px-8 py-4 rounded-lg hover:bg-[#006a62]/5 transition-colors text-center">
                Для партнёров
              </a>
            </div>
            <!-- Trust badges -->
            <div class="flex flex-wrap gap-6 text-sm text-[#45464d]">
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62]">shield</span>
                Безопасная оплата
              </div>
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62]">schedule</span>
                Результат за 5-10 мин
              </div>
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62]">support_agent</span>
                Поддержка 24/7
              </div>
            </div>
          </div>
          <!-- Right: Dashboard image -->
          <div class="relative">
            <div class="rounded-xl overflow-hidden border border-[#c6c6cd] shadow-2xl">
              <img
                alt="Dashboard Preview"
                class="w-full h-auto object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuD7epAI-l4-vnIB7hMmU-fwxbAgEB-8y89OIzjzNxaLsX_AtSRf37-yGwCnbKuNQ-kH3ZO_VEotjITvFFy1p9-Y2sD7sZpXJMtXivjla6D5GuHpAFA92XgvuoMeGM8O_uCfuslBud0A9cvDhkv8l7_-7a1QkaQCbd-An8BJmqPc4CSXWO0zR_MUjgBzVxWcVXBU-H6Nm0AkH8F0bgMn-i9OodTHl_igUp3FN52Mmc9iVuv3hxbwRltG05KmqegaQH1PG8rlzPv2m7Y"
              />
            </div>
            <!-- Floating stats card -->
            <div class="absolute -bottom-6 -left-6 bg-white rounded-xl shadow-xl p-4 border border-[#c6c6cd]">
              <div class="text-2xl font-bold text-[#006a62]">50 000+</div>
              <div class="text-sm text-[#45464d]">постов проанализировано</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Stats -->
      <section class="bg-[#006a62] py-12">
        <div class="max-w-7xl mx-auto px-6">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-8 text-center text-white">
            <div>
              <div class="text-4xl font-bold mb-2">3</div>
              <div class="text-sm opacity-80">платформы для анализа</div>
            </div>
            <div>
              <div class="text-4xl font-bold mb-2">100+</div>
              <div class="text-sm opacity-80">категорий бизнеса</div>
            </div>
            <div>
              <div class="text-4xl font-bold mb-2">5 мин</div>
              <div class="text-sm opacity-80">среднее время анализа</div>
            </div>
            <div>
              <div class="text-4xl font-bold mb-2">24/7</div>
              <div class="text-sm opacity-80">доступность сервиса</div>
            </div>
          </div>
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

      <!-- For Partners (Banks) -->
      <section id="partners" class="bg-gradient-to-br from-[#006a62] to-[#004d47] py-24">
        <div class="max-w-7xl mx-auto px-6">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div class="text-white">
              <div class="inline-flex items-center gap-2 bg-white/20 px-4 py-2 rounded-full text-sm font-medium mb-6">
                <span class="material-symbols-outlined text-lg">handshake</span>
                Партнёрская программа
              </div>
              <h2 class="text-3xl lg:text-4xl font-bold mb-6">Для банков и финансовых организаций</h2>
              <p class="text-lg opacity-90 mb-8 leading-relaxed">
                Предлагаем интеграцию BizMap в ваши продукты для предпринимателей. 
                Помогите клиентам найти прибыльную нишу — повысьте конверсию в РКО и кредитные продукты.
              </p>
              <ul class="space-y-4 mb-8">
                <li class="flex items-start gap-3">
                  <span class="material-symbols-outlined text-[#57fae9] mt-0.5">check_circle</span>
                  <span>White-label решение под ваш бренд</span>
                </li>
                <li class="flex items-start gap-3">
                  <span class="material-symbols-outlined text-[#57fae9] mt-0.5">check_circle</span>
                  <span>API-интеграция в личный кабинет клиента</span>
                </li>
                <li class="flex items-start gap-3">
                  <span class="material-symbols-outlined text-[#57fae9] mt-0.5">check_circle</span>
                  <span>Аналитика по сегментам и регионам</span>
                </li>
                <li class="flex items-start gap-3">
                  <span class="material-symbols-outlined text-[#57fae9] mt-0.5">check_circle</span>
                  <span>Повышение LTV клиентов на РКО</span>
                </li>
              </ul>
              <a href="mailto:nikmaltcev@vk.com?subject=Партнёрство BizMap" class="inline-flex items-center gap-2 bg-white text-[#006a62] font-semibold px-6 py-3 rounded-lg hover:bg-gray-100 transition-colors">
                <span class="material-symbols-outlined">mail</span>
                Обсудить партнёрство
              </a>
            </div>
            <div class="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-white/20">
              <h3 class="text-white text-xl font-semibold mb-6">Преимущества для банка</h3>
              <div class="space-y-6">
                <div class="flex items-start gap-4">
                  <div class="w-12 h-12 bg-[#57fae9]/20 rounded-lg flex items-center justify-center shrink-0">
                    <span class="material-symbols-outlined text-[#57fae9]">trending_up</span>
                  </div>
                  <div>
                    <div class="text-white font-semibold mb-1">+25% к конверсии в РКО</div>
                    <div class="text-white/70 text-sm">Клиенты с готовой бизнес-идеей охотнее открывают счёт</div>
                  </div>
                </div>
                <div class="flex items-start gap-4">
                  <div class="w-12 h-12 bg-[#57fae9]/20 rounded-lg flex items-center justify-center shrink-0">
                    <span class="material-symbols-outlined text-[#57fae9]">loyalty</span>
                  </div>
                  <div>
                    <div class="text-white font-semibold mb-1">Повышение лояльности</div>
                    <div class="text-white/70 text-sm">Дополнительная ценность для начинающих предпринимателей</div>
                  </div>
                </div>
                <div class="flex items-start gap-4">
                  <div class="w-12 h-12 bg-[#57fae9]/20 rounded-lg flex items-center justify-center shrink-0">
                    <span class="material-symbols-outlined text-[#57fae9]">analytics</span>
                  </div>
                  <div>
                    <div class="text-white font-semibold mb-1">Данные о клиентах</div>
                    <div class="text-white/70 text-sm">Понимание интересов и планов ваших клиентов</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Use Cases -->
      <section class="max-w-7xl mx-auto px-6 py-24">
        <div class="text-center mb-16">
          <h2 class="text-3xl font-semibold tracking-tight mb-4">Кому подходит BizMap</h2>
          <p class="text-[#45464d] max-w-2xl mx-auto">Наш сервис помогает разным категориям пользователей находить и валидировать бизнес-идеи</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div class="bg-white p-8 border border-[#c6c6cd] rounded-xl">
            <div class="w-14 h-14 bg-[#006a62]/10 rounded-xl flex items-center justify-center mb-6">
              <span class="material-symbols-outlined text-3xl text-[#006a62]">rocket_launch</span>
            </div>
            <h3 class="text-xl font-semibold mb-3">Начинающие предприниматели</h3>
            <p class="text-[#45464d] mb-4">Ищете первую бизнес-идею? Получите список проверенных ниш с реальным спросом и низким порогом входа.</p>
            <ul class="text-sm text-[#45464d] space-y-2">
              <li class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg">check</span>
                Идеи с минимальными вложениями
              </li>
              <li class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg">check</span>
                Готовый план запуска MVP
              </li>
            </ul>
          </div>
          <div class="bg-white p-8 border border-[#c6c6cd] rounded-xl">
            <div class="w-14 h-14 bg-[#006a62]/10 rounded-xl flex items-center justify-center mb-6">
              <span class="material-symbols-outlined text-3xl text-[#006a62]">store</span>
            </div>
            <h3 class="text-xl font-semibold mb-3">Действующий бизнес</h3>
            <p class="text-[#45464d] mb-4">Хотите расширить продуктовую линейку или выйти в смежную нишу? Найдите точки роста на основе данных.</p>
            <ul class="text-sm text-[#45464d] space-y-2">
              <li class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg">check</span>
                Анализ смежных рынков
              </li>
              <li class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg">check</span>
                Выявление новых потребностей
              </li>
            </ul>
          </div>
          <div class="bg-white p-8 border border-[#c6c6cd] rounded-xl">
            <div class="w-14 h-14 bg-[#006a62]/10 rounded-xl flex items-center justify-center mb-6">
              <span class="material-symbols-outlined text-3xl text-[#006a62]">account_balance</span>
            </div>
            <h3 class="text-xl font-semibold mb-3">Инвесторы и фонды</h3>
            <p class="text-[#45464d] mb-4">Оценивайте рыночный потенциал стартапов и находите перспективные направления для инвестиций.</p>
            <ul class="text-sm text-[#45464d] space-y-2">
              <li class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg">check</span>
                Валидация бизнес-моделей
              </li>
              <li class="flex items-center gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg">check</span>
                Анализ трендов рынка
              </li>
            </ul>
          </div>
        </div>
      </section>

      <!-- CTA -->
      <section class="bg-[#f6f3f5] py-24">
        <div class="max-w-4xl mx-auto px-6 text-center">
          <h2 class="text-3xl font-bold mb-4">Готовы найти свою нишу?</h2>
          <p class="text-lg text-[#45464d] mb-8">Первые 3 анализа бесплатно. Без регистрации и привязки карты.</p>
          <button
            class="bg-[#006a62] text-white text-lg font-semibold px-10 py-4 rounded-lg hover:bg-[#005a54] transition-colors shadow-lg"
            @click="goToApp"
          >
            Начать бесплатно
          </button>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="bg-slate-50 w-full mt-auto border-t border-slate-200 py-12 px-6">
      <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-start gap-8">
        <div>
          <div class="font-bold text-slate-900 text-lg mb-2">BizMap</div>
          <p class="text-xs text-slate-500">© 2025 BizMap. Профессиональная аналитика бизнес-ниш.</p>
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
