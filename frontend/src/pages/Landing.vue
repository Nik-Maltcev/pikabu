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
    <nav class="fixed top-0 w-full z-50 bg-white/80 backdrop-blur-md border-b border-slate-200 flex justify-between items-center px-4 md:px-6 h-14 md:h-16">
      <div class="max-w-7xl w-full mx-auto flex justify-between items-center">
        <div class="text-lg md:text-xl font-bold tracking-tight text-slate-900">BizMap</div>
        <div class="hidden md:flex gap-6">
          <router-link to="/app" class="text-cyan-600 border-b-2 border-cyan-600 pb-1 text-sm font-medium">Поиск ниш</router-link>
          <router-link to="/account" class="text-slate-600 hover:text-slate-900 text-sm font-medium">Мои отчеты</router-link>
          <router-link to="/pricing" class="text-slate-600 hover:text-slate-900 text-sm font-medium">Тарифы</router-link>
        </div>
        <router-link to="/account" class="bg-black text-white text-xs font-medium px-3 md:px-4 py-2 rounded-lg hover:opacity-80 transition-opacity no-underline">Войти</router-link>
      </div>
    </nav>

    <main class="flex-grow pt-20 md:pt-24 pb-16">
      <!-- Hero -->
      <section class="max-w-7xl mx-auto px-4 md:px-6 pt-8 md:pt-12 pb-12 md:pb-24">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <!-- Left: Text -->
          <div class="text-left">
            <div class="inline-flex items-center gap-2 bg-[#006a62]/10 text-[#006a62] px-3 py-1.5 rounded-full text-sm md:text-sm font-medium mb-4 md:mb-6">
              <span class="material-symbols-outlined text-base md:text-lg">verified</span>
              Аналитика на основе реальных данных
            </div>
            <h1 class="text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight leading-tight mb-3 md:mb-6">
              Найдите прибыльную нишу для бизнеса за 5 минут
            </h1>
            <p class="text-base md:text-lg text-[#45464d] mb-5 md:mb-8 leading-relaxed">
              ИИ-платформа анализирует тысячи обсуждений на Pikabu, Habr и VC.ru, выявляет боли аудитории и генерирует готовые бизнес-идеи с планом запуска.
            </p>
            <div class="flex flex-col sm:flex-row gap-3 md:gap-4 mb-5 md:mb-8">
              <button
                class="bg-[#006a62] text-white text-base md:text-lg font-semibold px-5 sm:px-6 md:px-8 py-3 md:py-4 rounded-lg hover:bg-[#005a54] transition-colors shadow-lg"
                @click="goToApp"
              >
                Начать анализ бесплатно
              </button>
              <a href="#partners" class="border-2 border-[#006a62] text-[#006a62] text-base md:text-lg font-semibold px-5 sm:px-6 md:px-8 py-3 md:py-4 rounded-lg hover:bg-[#006a62]/5 transition-colors text-center">
                Для партнёров
              </a>
            </div>
            <!-- Trust badges -->
            <div class="flex flex-wrap gap-3 md:gap-6 text-sm md:text-sm text-[#45464d]">
              <div class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-[#006a62] text-base md:text-xl">shield</span>
                Безопасная оплата
              </div>
              <div class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-[#006a62] text-base md:text-xl">schedule</span>
                Результат за 5-10 мин
              </div>
              <div class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-[#006a62] text-base md:text-xl">support_agent</span>
                Поддержка 24/7
              </div>
            </div>
          </div>
          <!-- Right: Dashboard image -->
          <div class="relative hidden lg:block">
            <div class="rounded-xl overflow-hidden border border-[#c6c6cd] shadow-2xl">
              <img
                alt="Dashboard Preview"
                class="w-full h-auto object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuD7epAI-l4-vnIB7hMmU-fwxbAgEB-8y89OIzjzNxaLsX_AtSRf37-yGwCnbKuNQ-kH3ZO_VEotjITvFFy1p9-Y2sD7sZpXJMtXivjla6D5GuHpAFA92XgvuoMeGM8O_uCfuslBud0A9cvDhkv8l7_-7a1QkaQCbd-An8BJmqPc4CSXWO0zR_MUjgBzVxWcVXBU-H6Nm0AkH8F0bgMn-i9OodTHl_igUp3FN52Mmc9iVuv3hxbwRltG05KmqegaQH1PG8rlzPv2m7Y"
              />
            </div>
            <!-- Floating stats card - visible on lg+ -->
            <div class="hidden lg:block absolute -bottom-6 -left-6 bg-white rounded-xl shadow-xl p-4 border border-[#c6c6cd]">
              <div class="text-2xl font-bold text-[#006a62]">50 000+</div>
              <div class="text-sm text-[#45464d]">постов проанализировано</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Stats -->
      <section class="bg-[#006a62] py-8 md:py-12 mt-8 lg:mt-0">
        <div class="max-w-7xl mx-auto px-6">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-8 text-center text-white">
            <div>
              <div class="text-2xl md:text-4xl font-bold mb-1 md:mb-2">3</div>
              <div class="text-xs md:text-sm opacity-80">платформы</div>
            </div>
            <div>
              <div class="text-2xl md:text-4xl font-bold mb-1 md:mb-2">100+</div>
              <div class="text-xs md:text-sm opacity-80">категорий</div>
            </div>
            <div>
              <div class="text-2xl md:text-4xl font-bold mb-1 md:mb-2">5 мин</div>
              <div class="text-xs md:text-sm opacity-80">анализ</div>
            </div>
            <div>
              <div class="text-2xl md:text-4xl font-bold mb-1 md:mb-2">24/7</div>
              <div class="text-xs md:text-sm opacity-80">доступность</div>
            </div>
          </div>
        </div>
      </section>

      <!-- How it works -->
      <section class="bg-[#f6f3f5] py-16 md:py-24">
        <div class="max-w-7xl mx-auto px-4 md:px-6">
          <h2 class="text-2xl md:text-3xl font-semibold tracking-tight text-center mb-12 md:mb-16">Как это работает</h2>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
            <div class="bg-white p-6 md:p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-14 h-14 md:w-16 md:h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-4 md:mb-6">
                <span class="material-symbols-outlined text-2xl md:text-3xl icon-fill">database</span>
              </div>
              <h3 class="text-lg md:text-xl font-semibold mb-3 md:mb-4">Сбор данных</h3>
              <p class="text-sm text-[#45464d] leading-relaxed">
                Собираем посты и комментарии с Pikabu, Habr и VC.ru по выбранной категории за 14-30 дней.
              </p>
            </div>
            <div class="bg-white p-6 md:p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-14 h-14 md:w-16 md:h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-4 md:mb-6">
                <span class="material-symbols-outlined text-2xl md:text-3xl icon-fill">psychology</span>
              </div>
              <h3 class="text-lg md:text-xl font-semibold mb-3 md:mb-4">ИИ-анализ</h3>
              <p class="text-sm text-[#45464d] leading-relaxed">
                Нейросеть анализирует боли аудитории, выявляет паттерны и генерирует бизнес-идеи.
              </p>
            </div>
            <div class="bg-white p-6 md:p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-14 h-14 md:w-16 md:h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-4 md:mb-6">
                <span class="material-symbols-outlined text-2xl md:text-3xl icon-fill">description</span>
              </div>
              <h3 class="text-lg md:text-xl font-semibold mb-3 md:mb-4">Готовый отчёт</h3>
              <p class="text-sm text-[#45464d] leading-relaxed">
                Получаете структурированный отчёт с нишами, JTBD-анализом и планом запуска MVP.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- Report Example -->
      <section class="max-w-7xl mx-auto px-4 md:px-6 py-16 md:py-24">
        <div class="text-center mb-10 md:mb-12">
          <h2 class="text-2xl md:text-3xl font-semibold tracking-tight mb-3 md:mb-4">Пример отчёта</h2>
          <p class="text-[#45464d]">Вот что вы получите после анализа категории «Маркетинг»</p>
        </div>
        
        <!-- Mock Report -->
        <div class="max-w-3xl mx-auto bg-white border border-[#c6c6cd] rounded-2xl overflow-hidden shadow-lg">
          <!-- Report Header -->
          <div class="bg-gradient-to-r from-[#006a62] to-[#004d47] text-white p-4 md:p-6">
            <div class="flex items-center gap-3 mb-2">
              <span class="material-symbols-outlined">analytics</span>
              <span class="font-semibold">Отчёт: Поиск ниши</span>
            </div>
            <div class="text-sm opacity-80">Категория: Маркетинг · Период: 14 дней · 3 платформы</div>
          </div>
          
          <!-- Key Pains -->
          <div class="p-4 md:p-6 border-b border-[#e5e5e5]">
            <h3 class="font-semibold text-[#1b1b1d] mb-4 flex items-center gap-2">
              <span>🔥</span> ТОП Ключевых болей
            </h3>
            <div class="space-y-3">
              <div class="border border-[#e5e5e5] rounded-lg p-3 md:p-4">
                <div class="flex flex-wrap items-start justify-between gap-2 mb-2">
                  <span class="font-medium text-[#1b1b1d] text-sm md:text-base">Сложно найти первых клиентов без бюджета</span>
                  <div class="flex gap-1.5">
                    <span class="text-xs px-2 py-0.5 rounded bg-red-50 text-red-700">Массово</span>
                    <span class="text-xs px-2 py-0.5 rounded bg-orange-50 text-orange-700">Высокий</span>
                  </div>
                </div>
                <p class="text-xs md:text-sm text-[#6b7280] italic">«Запустил лендинг, а трафика ноль. Денег на рекламу нет...»</p>
              </div>
              <div class="border border-[#e5e5e5] rounded-lg p-3 md:p-4">
                <div class="flex flex-wrap items-start justify-between gap-2 mb-2">
                  <span class="font-medium text-[#1b1b1d] text-sm md:text-base">Не понимают как считать unit-экономику</span>
                  <div class="flex gap-1.5">
                    <span class="text-xs px-2 py-0.5 rounded bg-orange-50 text-orange-700">Часто</span>
                    <span class="text-xs px-2 py-0.5 rounded bg-yellow-50 text-yellow-700">Средний</span>
                  </div>
                </div>
                <p class="text-xs md:text-sm text-[#6b7280] italic">«Вроде продажи есть, а прибыли нет. Где теряю?»</p>
              </div>
              <div class="border border-[#e5e5e5] rounded-lg p-3 md:p-4 opacity-50 blur-[2px]">
                <div class="flex items-start justify-between gap-2">
                  <span class="font-medium text-[#1b1b1d]">████████ ██████ ████</span>
                  <div class="flex gap-1.5">
                    <span class="text-xs px-2 py-0.5 rounded bg-gray-100">███</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Business Ideas -->
          <div class="p-4 md:p-6 border-b border-[#e5e5e5]">
            <h3 class="font-semibold text-[#1b1b1d] mb-4 flex items-center gap-2">
              <span>💡</span> Бизнес-идеи
            </h3>
            <div class="space-y-3">
              <div class="border border-[#e5e5e5] rounded-lg p-3 md:p-4">
                <div class="flex flex-wrap items-start justify-between gap-2 mb-2">
                  <span class="font-medium text-[#1b1b1d] text-sm md:text-base">Калькулятор unit-экономики для новичков</span>
                  <div class="flex gap-1.5">
                    <span class="text-xs px-2 py-0.5 rounded bg-green-50 text-green-700">Спрос: Высокий</span>
                  </div>
                </div>
                <p class="text-xs md:text-sm text-[#6b7280] mb-3">Простой онлайн-инструмент с шаблонами для разных ниш. Монетизация через премиум-шаблоны.</p>
                <div class="bg-purple-50 rounded-lg p-3">
                  <div class="text-xs font-semibold text-purple-900 mb-1">🚀 MVP за выходные:</div>
                  <p class="text-xs text-purple-800">Google Sheets шаблон + Tilda лендинг + Telegram-бот для расчётов</p>
                </div>
              </div>
              <div class="border border-[#e5e5e5] rounded-lg p-3 md:p-4 opacity-50 blur-[2px]">
                <span class="font-medium text-[#1b1b1d]">████████ ██████</span>
              </div>
            </div>
          </div>
          
          <!-- Locked sections hint -->
          <div class="p-4 md:p-6 bg-[#f9fafb] text-center">
            <div class="flex items-center justify-center gap-2 text-[#6b7280] text-sm mb-3">
              <span class="material-symbols-outlined text-lg">lock</span>
              <span>JTBD-анализ, тренды и рекомендации — в полном отчёте</span>
            </div>
            <button
              class="bg-[#006a62] text-white font-semibold px-6 py-2.5 rounded-lg hover:bg-[#005a54] transition-colors text-sm"
              @click="goToApp"
            >
              Получить такой отчёт
            </button>
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

      <!-- For Partners -->
      <section id="partners" class="bg-gradient-to-br from-[#006a62] to-[#004d47] py-16 md:py-24">
        <div class="max-w-5xl mx-auto px-4 md:px-6">
          <div class="text-center text-white">
            <div class="inline-flex items-center gap-2 bg-white/20 px-4 py-2 rounded-full text-sm font-medium mb-6">
              <span class="material-symbols-outlined text-lg">handshake</span>
              Партнёрская программа
            </div>
            <h2 class="text-2xl md:text-4xl font-bold mb-4 md:mb-6">Разместите BizMap на своей витрине</h2>
            <p class="text-base md:text-lg opacity-90 mb-8 max-w-2xl mx-auto leading-relaxed">
              Предлагаем банкам, акселераторам и бизнес-сообществам добавить BizMap в каталог сервисов для предпринимателей. Помогите вашим клиентам найти прибыльную нишу.
            </p>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 md:gap-6 mb-8 max-w-3xl mx-auto">
              <div class="bg-white/10 backdrop-blur-sm rounded-xl p-4 md:p-6 border border-white/20">
                <span class="material-symbols-outlined text-[#57fae9] text-3xl mb-3">account_balance</span>
                <div class="font-semibold mb-1">Банки</div>
                <div class="text-sm opacity-70">Витрина сервисов для РКО</div>
              </div>
              <div class="bg-white/10 backdrop-blur-sm rounded-xl p-4 md:p-6 border border-white/20">
                <span class="material-symbols-outlined text-[#57fae9] text-3xl mb-3">rocket_launch</span>
                <div class="font-semibold mb-1">Акселераторы</div>
                <div class="text-sm opacity-70">Инструмент для резидентов</div>
              </div>
              <div class="bg-white/10 backdrop-blur-sm rounded-xl p-4 md:p-6 border border-white/20">
                <span class="material-symbols-outlined text-[#57fae9] text-3xl mb-3">groups</span>
                <div class="font-semibold mb-1">Сообщества</div>
                <div class="text-sm opacity-70">Польза для участников</div>
              </div>
            </div>
            <a href="mailto:nikmaltcev@vk.com?subject=Партнёрство BizMap" class="inline-flex items-center gap-2 bg-white text-[#006a62] font-semibold px-6 py-3 rounded-lg hover:bg-gray-100 transition-colors">
              <span class="material-symbols-outlined">mail</span>
              Обсудить сотрудничество
            </a>
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

      <!-- Pricing -->
      <section class="max-w-7xl mx-auto px-4 md:px-6 py-16 md:py-24">
        <div class="text-center mb-12">
          <h2 class="text-2xl md:text-3xl font-semibold tracking-tight mb-4">Тарифы</h2>
          <p class="text-[#45464d]">Простая и прозрачная модель оплаты</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <!-- Free -->
          <div class="bg-white border border-[#c6c6cd] rounded-xl p-6 md:p-8">
            <div class="text-xs font-semibold text-green-700 bg-green-50 px-3 py-1 rounded-full w-fit mb-4">БЕСПЛАТНО</div>
            <h3 class="text-lg font-semibold text-[#1b1b1d] mb-2">Превью отчёта</h3>
            <p class="text-3xl font-bold text-[#1b1b1d] mb-4">0 ₽</p>
            <ul class="text-sm text-[#44474d] space-y-2 mb-6">
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-green-600 text-lg mt-0.5">check</span>
                3–5 лучших ниш по категории
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-green-600 text-lg mt-0.5">check</span>
                Краткое описание потенциала
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-green-600 text-lg mt-0.5">check</span>
                Период анализа: 14 дней
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[#45464d] text-lg mt-0.5">close</span>
                <span class="text-[#76777d]">3 анализа на устройство</span>
              </li>
            </ul>
            <button
              class="w-full border-2 border-[#006a62] text-[#006a62] font-semibold py-3 rounded-lg hover:bg-[#006a62]/5 transition-colors"
              @click="goToApp"
            >
              Попробовать
            </button>
          </div>
          <!-- Paid -->
          <div class="bg-white border-2 border-[#006a62] rounded-xl p-6 md:p-8 relative">
            <div class="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#006a62] text-white text-xs font-semibold px-4 py-1 rounded-full">ПОПУЛЯРНЫЙ</div>
            <div class="text-xs font-semibold text-[#006a62] bg-[#57fae9]/20 px-3 py-1 rounded-full w-fit mb-4">ПОЛНЫЙ ДОСТУП</div>
            <h3 class="text-lg font-semibold text-[#1b1b1d] mb-2">Полный отчёт</h3>
            <p class="text-3xl font-bold text-[#1b1b1d] mb-4">4 990 ₽</p>
            <ul class="text-sm text-[#44474d] space-y-2 mb-6">
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg mt-0.5">check</span>
                Все найденные ниши без ограничений
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg mt-0.5">check</span>
                JTBD-анализ целевой аудитории
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg mt-0.5">check</span>
                MVP-план и оценка рисков
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg mt-0.5">check</span>
                Период анализа: до 30 дней
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[#006a62] text-lg mt-0.5">check</span>
                Бессрочный доступ к отчёту
              </li>
            </ul>
            <button
              class="w-full bg-[#006a62] text-white font-semibold py-3 rounded-lg hover:bg-[#005a54] transition-colors"
              @click="goToApp"
            >
              Получить полный отчёт
            </button>
          </div>
        </div>
      </section>

      <!-- FAQ -->
      <section class="bg-[#f6f3f5] py-16 md:py-24">
        <div class="max-w-3xl mx-auto px-4 md:px-6">
          <h2 class="text-2xl md:text-3xl font-semibold tracking-tight text-center mb-10 md:mb-12">Частые вопросы</h2>
          <div class="space-y-4">
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Откуда берутся данные для анализа?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-sm text-[#45464d] leading-relaxed">
                Мы собираем публичные посты и комментарии с трёх русскоязычных площадок: Pikabu, Habr и VC.ru. Это реальные обсуждения реальных людей — не опросы и не фокус-группы.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Сколько времени занимает анализ?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-sm text-[#45464d] leading-relaxed">
                Обычно 5-10 минут. Можете подождать на странице или оставить email/Telegram — пришлём уведомление когда отчёт будет готов.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Что если ниша мне не подойдёт?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-sm text-[#45464d] leading-relaxed">
                Отчёт показывает объективную картину на основе данных. Если в категории мало болей или идей — это тоже ценная информация, которая сэкономит вам время. Попробуйте другую категорию — первые 3 анализа бесплатны.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Можно ли вернуть деньги?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-sm text-[#45464d] leading-relaxed">
                Возврат возможен если отчёт не был сгенерирован из-за технической ошибки. Напишите на nikmaltcev@vk.com в течение 7 дней с момента оплаты.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Как долго хранится отчёт?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-sm text-[#45464d] leading-relaxed">
                Бессрочно. После оплаты полный отчёт доступен по уникальной ссылке в любое время. Рекомендуем сохранить ссылку или зарегистрироваться — тогда все отчёты будут в личном кабинете.
              </div>
            </details>
          </div>
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
