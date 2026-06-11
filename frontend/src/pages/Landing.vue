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
        <div class="text-[38px] md:text-xl font-bold tracking-tight text-slate-900">BizMap</div>
        <div class="hidden md:flex gap-6">
          <router-link to="/app" class="text-cyan-600 border-b-2 border-cyan-600 pb-1 text-[29px] md:text-sm font-medium">Поиск ниш</router-link>
          <router-link to="/account" class="text-slate-600 hover:text-slate-900 text-[29px] md:text-sm font-medium">Мои отчеты</router-link>
          <a href="#pricing" class="text-slate-600 hover:text-slate-900 text-[29px] md:text-sm font-medium">Тарифы</a>
        </div>
        <router-link to="/account" class="bg-black text-white text-[25px] md:text-xs font-medium px-3 md:px-4 py-2 rounded-lg hover:opacity-80 transition-opacity no-underline">Войти</router-link>
      </div>
    </nav>

    <main class="flex-grow pt-[50px] md:pt-24 pb-[20px] md:pb-16">
      <!-- Hero -->
      <section class="max-w-7xl mx-auto px-4 md:px-6 pt-[10px] md:pt-12 pb-[10px] md:pb-24">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <!-- Left: Text -->
          <div class="text-left">
            <div class="inline-flex items-center gap-2 bg-[#006a62]/10 text-[#006a62] px-3 py-1.5 rounded-full text-sm md:text-sm font-medium mb-[10px] md:mb-6">
              <span class="material-symbols-outlined text-base md:text-lg">verified</span>
              Аналитика на основе реальных данных
            </div>
            <h1 class="text-[62px] md:text-4xl lg:text-5xl font-bold tracking-tight leading-tight mb-[10px] md:mb-6">
              Анализируем 50 000+ постов и находим прибыльные ниши за 5 минут
            </h1>
            <p class="text-base md:text-lg text-[#45464d] mb-[14px] md:mb-8 leading-relaxed">
              ИИ обрабатывает реальные обсуждения с крупнейших русскоязычных площадок, выявляет боли аудитории и выдаёт готовые бизнес-идеи с MVP-планом.
            </p>
            <div class="flex flex-col sm:flex-row gap-3 md:gap-4 mb-[10px] md:mb-8">
              <button
                class="bg-[#006a62] text-white text-base md:text-lg font-semibold px-5 sm:px-6 md:px-8 py-3 md:py-4 rounded-lg hover:bg-[#005a54] transition-colors shadow-lg"
                @click="goToApp"
              >
                Начать анализ бесплатно
              </button>
            </div>
            <!-- Trust badges -->
            <div class="flex flex-wrap gap-3 md:gap-6 text-base md:text-base text-[#45464d]">
              <div class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-[#006a62] text-xl md:text-xl">shield</span>
                Безопасная оплата
              </div>
              <div class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-[#006a62] text-xl md:text-xl">schedule</span>
                Результат за 5-10 мин
              </div>
              <div class="flex items-center gap-1.5">
                <span class="material-symbols-outlined text-[#006a62] text-xl md:text-xl">support_agent</span>
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
              <div class="text-base text-[#45464d]">постов проанализировано</div>
            </div>
          </div>
        </div>
      </section>

      <!-- Stats -->
      <section class="bg-[#006a62] py-[16px] md:py-12 mt-[20px] lg:mt-0">
        <div class="max-w-7xl mx-auto px-[12px] md:px-6">
          <div class="grid grid-cols-3 gap-[12px] md:gap-8 text-center text-white">
            <div>
              <div class="text-[28px] md:text-4xl font-bold whitespace-nowrap">10+</div>
              <div class="text-[13px] md:text-sm opacity-80 leading-tight">категорий</div>
            </div>
            <div>
              <div class="text-[28px] md:text-4xl font-bold whitespace-nowrap">5 <span class="text-[18px] md:text-2xl">минут</span></div>
              <div class="text-[13px] md:text-sm opacity-80 leading-tight">анализ</div>
            </div>
            <div>
              <div class="text-[28px] md:text-4xl font-bold whitespace-nowrap">24/7</div>
              <div class="text-[13px] md:text-sm opacity-80 leading-tight">доступность</div>
            </div>
          </div>
        </div>
      </section>

      <!-- How it works -->
      <section class="bg-[#f6f3f5] py-[40px] md:py-24">
        <div class="max-w-7xl mx-auto px-4 md:px-6">
          <h2 class="text-2xl md:text-3xl font-semibold tracking-tight text-center mb-[30px] md:mb-16">Как это работает</h2>
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-[16px] md:gap-8">
            <div class="bg-white p-[16px] md:p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-14 h-14 md:w-16 md:h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-[12px] md:mb-6">
                <span class="material-symbols-outlined text-2xl md:text-3xl icon-fill">database</span>
              </div>
              <h3 class="text-[38px] md:text-xl font-semibold mb-[8px] md:mb-4">Сбор данных</h3>
              <p class="text-[35px] md:text-base text-[#45464d] leading-relaxed">
                Собираем посты и комментарии с популярных русскоязычных площадок по выбранной категории за 14-30 дней.
              </p>
            </div>
            <div class="bg-white p-[16px] md:p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-14 h-14 md:w-16 md:h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-[12px] md:mb-6">
                <span class="material-symbols-outlined text-2xl md:text-3xl icon-fill">psychology</span>
              </div>
              <h3 class="text-[38px] md:text-xl font-semibold mb-[8px] md:mb-4">ИИ-анализ</h3>
              <p class="text-[35px] md:text-base text-[#45464d] leading-relaxed">
                Нейросеть анализирует боли аудитории, выявляет паттерны и генерирует бизнес-идеи.
              </p>
            </div>
            <div class="bg-white p-[16px] md:p-8 border border-[#c6c6cd] rounded-xl flex flex-col items-center text-center">
              <div class="w-14 h-14 md:w-16 md:h-16 bg-[#dae2fd] text-[#131b2e] rounded-full flex items-center justify-center mb-[12px] md:mb-6">
                <span class="material-symbols-outlined text-2xl md:text-3xl icon-fill">description</span>
              </div>
              <h3 class="text-[38px] md:text-xl font-semibold mb-[8px] md:mb-4">Готовый отчёт</h3>
              <p class="text-[35px] md:text-base text-[#45464d] leading-relaxed">
                Получаете структурированный отчёт с нишами, JTBD-анализом и планом запуска MVP.
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- Why BizMap vs ChatGPT -->
      <section class="max-w-7xl mx-auto px-4 md:px-6 py-16 md:py-24">
        <div class="text-center mb-10 md:mb-14">
          <h2 class="text-2xl md:text-3xl font-semibold tracking-tight mb-3">Почему BizMap, а не ChatGPT?</h2>
          <p class="text-[#45464d] max-w-2xl mx-auto">Мы парсим реальные обсуждения живых людей с Пикабу и VC.ru. ChatGPT работает с маркетинговыми статьями и фантазирует.</p>
        </div>

        <!-- Comparison Table -->
        <div class="max-w-3xl mx-auto overflow-hidden rounded-xl border border-[#c6c6cd] shadow-sm">
          <table class="w-full text-left text-sm md:text-base">
            <thead>
              <tr class="bg-[#f6f3f5]">
                <th class="p-3 md:p-4 font-semibold text-[#1b1b1d]">Возможность</th>
                <th class="p-3 md:p-4 font-semibold text-[#006a62] text-center">BizMap</th>
                <th class="p-3 md:p-4 font-semibold text-[#6b7280] text-center">ChatGPT</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#e5e5e5]">
              <tr class="bg-white">
                <td class="p-3 md:p-4">Реальные данные с форумов (50 000+ постов)</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-red-400">✗</td>
              </tr>
              <tr class="bg-[#fafafa]">
                <td class="p-3 md:p-4">Свежие данные (обновление каждые 3 дня)</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-red-400">✗</td>
              </tr>
              <tr class="bg-white">
                <td class="p-3 md:p-4">Цитаты из реальных обсуждений</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-red-400">✗</td>
              </tr>
              <tr class="bg-[#fafafa]">
                <td class="p-3 md:p-4">Количественный рейтинг упоминаний болей</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-red-400">✗</td>
              </tr>
              <tr class="bg-white">
                <td class="p-3 md:p-4">JTBD-анализ на реальных данных</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-yellow-500">~</td>
              </tr>
              <tr class="bg-[#fafafa]">
                <td class="p-3 md:p-4">MVP-план с конкретными инструментами</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-yellow-500">~</td>
              </tr>
              <tr class="bg-white">
                <td class="p-3 md:p-4">Аналоги и конкуренты с выручкой</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-red-400">✗</td>
              </tr>
              <tr class="bg-[#fafafa]">
                <td class="p-3 md:p-4">Работает без промпт-инжиниринга</td>
                <td class="p-3 md:p-4 text-center text-green-600 font-bold">✓</td>
                <td class="p-3 md:p-4 text-center text-red-400">✗</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Key differentiator -->
        <div class="max-w-3xl mx-auto mt-8 bg-gradient-to-r from-[#ecfdf5] to-[#f0f9ff] border border-[#a7f3d0] rounded-xl p-5 md:p-6 flex items-start gap-4">
          <span class="material-symbols-outlined text-[#006a62] text-3xl shrink-0 mt-0.5">database</span>
          <div>
            <h4 class="font-semibold text-[#1b1b1d] mb-1">Данные от живых людей, а не из интернет-статей</h4>
            <p class="text-sm text-[#45464d] leading-relaxed">BizMap парсит тысячи постов и комментариев с Пикабу и VC.ru — это реальные жалобы, вопросы и потребности аудитории. ChatGPT генерирует ответы из обучающих данных, которые часто устаревшие и лишены контекста.</p>
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

      <!-- Benefits -->
      <section class="max-w-7xl mx-auto px-4 md:px-6 py-[40px] md:py-24">
        <h2 class="text-2xl md:text-3xl font-semibold tracking-tight mb-[20px] md:mb-12">Преимущества</h2>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-[16px] md:gap-6">
          <div class="bg-[#fcf8fa] p-[16px] md:p-8 border border-[#c6c6cd] rounded-xl flex items-start gap-4">
            <span class="material-symbols-outlined text-3xl text-[#006a62] shrink-0">speed</span>
            <div>
              <h3 class="text-lg md:text-xl font-semibold mb-1">5 минут вместо недель</h3>
              <p class="text-base text-[#45464d]">Автоматический анализ тысяч обсуждений, на который вручную ушли бы дни.</p>
            </div>
          </div>
          <div class="bg-[#fcf8fa] p-[16px] md:p-8 border border-[#c6c6cd] rounded-xl flex items-start gap-4">
            <span class="material-symbols-outlined text-3xl text-[#006a62] shrink-0">trending_up</span>
            <div>
              <h3 class="text-lg md:text-xl font-semibold mb-1">Данные, а не интуиция</h3>
              <p class="text-base text-[#45464d]">Решения на основе реальных болей живых людей, а не маркетинговых опросов.</p>
            </div>
          </div>
          <div class="bg-[#fcf8fa] p-[16px] md:p-8 border border-[#c6c6cd] rounded-xl flex items-start gap-4">
            <span class="material-symbols-outlined text-3xl text-[#006a62] shrink-0">insights</span>
            <div>
              <h3 class="text-lg md:text-xl font-semibold mb-1">От боли до MVP</h3>
              <p class="text-base text-[#45464d]">Полный путь: боли → JTBD → идея → план запуска. Всё в одном отчёте.</p>
            </div>
          </div>
          <div class="bg-[#fcf8fa] p-[16px] md:p-8 border border-[#c6c6cd] rounded-xl flex items-start gap-4">
            <span class="material-symbols-outlined text-3xl text-[#006a62] shrink-0">update</span>
            <div>
              <h3 class="text-lg md:text-xl font-semibold mb-1">Всегда свежие данные</h3>
              <p class="text-base text-[#45464d]">Парсинг каждые 3 дня. Вы видите актуальную картину рынка, а не прошлогоднюю.</p>
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
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div class="bg-white p-8 border border-[#c6c6cd] rounded-xl">
            <div class="w-14 h-14 bg-[#006a62]/10 rounded-xl flex items-center justify-center mb-6">
              <span class="material-symbols-outlined text-3xl text-[#006a62]">rocket_launch</span>
            </div>
            <h3 class="text-xl font-semibold mb-3">Начинающие предприниматели</h3>
            <p class="text-[#45464d] mb-4">Ищете первую бизнес-идею? Получите список проверенных ниш с реальным спросом и низким порогом входа.</p>
            <ul class="text-base text-[#45464d] space-y-2">
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
            <ul class="text-base text-[#45464d] space-y-2">
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
            <ul class="text-base text-[#45464d] space-y-2">
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
      <section id="pricing" class="max-w-7xl mx-auto px-4 md:px-6 py-16 md:py-24">
        <div class="text-center mb-12">
          <h2 class="text-2xl md:text-3xl font-semibold tracking-tight mb-4">Тарифы</h2>
          <p class="text-[#45464d]">Простая и прозрачная модель оплаты</p>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 max-w-4xl mx-auto">
          <!-- Free -->
          <div class="bg-white border border-[#c6c6cd] rounded-xl p-6 md:p-8">
            <div class="text-xs font-semibold text-green-700 bg-green-50 px-3 py-1 rounded-full w-fit mb-4">БЕСПЛАТНО</div>
            <h3 class="text-lg font-semibold text-[#1b1b1d] mb-2">Демо-отчёт</h3>
            <p class="text-3xl font-bold text-[#1b1b1d] mb-4">0 ₽</p>
            <ul class="text-base text-[#44474d] space-y-2 mb-6">
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-green-600 text-lg mt-0.5">check</span>
                1 бесплатный демо-анализ
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-green-600 text-lg mt-0.5">check</span>
                Покажем 3–5 ниш с кратким описанием
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-green-600 text-lg mt-0.5">check</span>
                Период анализа: 14 дней
              </li>
              <li class="flex items-start gap-2">
                <span class="material-symbols-outlined text-[#45464d] text-lg mt-0.5">close</span>
                <span class="text-[#76777d]">Без детального разбора и MVP-плана</span>
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
            <p class="text-3xl font-bold text-[#1b1b1d] mb-4">1 490 ₽</p>
            <ul class="text-base text-[#44474d] space-y-2 mb-6">
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
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-base text-[#45464d] leading-relaxed">
                Мы анализируем публичные обсуждения на популярных русскоязычных форумах и площадках. Это реальные мнения реальных людей — не опросы и не фокус-группы.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Сколько времени занимает анализ?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-base text-[#45464d] leading-relaxed">
                Обычно 5-10 минут. Можете подождать на странице или оставить email/Telegram — пришлём уведомление когда отчёт будет готов.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Что если ниша мне не подойдёт?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-base text-[#45464d] leading-relaxed">
                Отчёт показывает объективную картину на основе данных. Если в категории мало болей или идей — это тоже ценная информация, которая сэкономит вам время. Попробуйте другую категорию — первые 3 анализа бесплатны.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Можно ли вернуть деньги?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-base text-[#45464d] leading-relaxed">
                Возврат возможен если отчёт не был сгенерирован из-за технической ошибки. Напишите на nikmaltcev@vk.com в течение 7 дней с момента оплаты.
              </div>
            </details>
            <details class="bg-white border border-[#c6c6cd] rounded-xl group">
              <summary class="flex items-center justify-between p-4 md:p-5 cursor-pointer list-none">
                <span class="font-medium text-[#1b1b1d] text-sm md:text-base pr-4">Как долго хранится отчёт?</span>
                <span class="material-symbols-outlined text-[#006a62] transition-transform group-open:rotate-180">expand_more</span>
              </summary>
              <div class="px-4 md:px-5 pb-4 md:pb-5 text-base text-[#45464d] leading-relaxed">
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
