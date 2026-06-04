<script setup lang="ts">
</script>

<template>
  <div class="bg-[#fcf8fa] text-[#1b1b1d] min-h-screen flex flex-col font-['Inter']">
    <nav class="fixed top-0 w-full z-50 border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div class="flex justify-between items-center px-6 h-16 max-w-7xl mx-auto">
        <router-link to="/" class="text-xl font-bold tracking-tight text-slate-900 no-underline">BizMap</router-link>
      </div>
    </nav>

    <main class="flex-grow pt-24 pb-16 px-6 max-w-4xl mx-auto w-full">
      <h1 class="text-3xl font-bold mb-2">Услуги и цены</h1>
      <p class="text-sm text-[#76777d] mb-8">Описание услуг сервиса BizMap</p>

      <div class="space-y-8">

        <!-- Описание сервиса -->
        <section class="bg-white border border-[#c6c6cd] rounded-xl p-8">
          <h2 class="text-xl font-semibold text-[#1b1b1d] mb-4">О сервисе</h2>
          <p class="text-base text-[#44474d] leading-relaxed">
            BizMap — сервис автоматического поиска и анализа бизнес-ниш с использованием искусственного интеллекта. 
            Система собирает данные из открытых источников (форумы, социальные сети, тематические площадки), 
            анализирует боли и потребности аудитории, оценивает конкурентную среду и генерирует структурированные 
            аналитические отчёты с рекомендациями по запуску бизнеса.
          </p>
        </section>

        <!-- Товары/услуги с ценами -->
        <section>
          <h2 class="text-xl font-semibold text-[#1b1b1d] mb-4">Перечень услуг</h2>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <!-- Бесплатный -->
            <div class="bg-white border border-[#c6c6cd] rounded-xl p-6">
              <div class="text-xs font-semibold text-green-700 bg-green-50 px-3 py-1 rounded-full w-fit mb-4">БЕСПЛАТНО</div>
              <h3 class="text-lg font-semibold text-[#1b1b1d] mb-2">Превью отчёта</h3>
              <p class="text-2xl font-bold text-[#1b1b1d] mb-4">0 ₽</p>
              <p class="text-sm text-[#44474d] mb-4">Ознакомительный доступ к результатам анализа.</p>
              <h4 class="text-sm font-semibold text-[#1b1b1d] mb-2">Характеристики:</h4>
              <ul class="text-sm text-[#44474d] space-y-1.5 list-disc pl-5">
                <li>3–5 лучших ниш по выбранной категории</li>
                <li>Краткое описание потенциала каждой ниши</li>
                <li>Уровень спроса (высокий / средний / низкий)</li>
                <li>Период анализа: 14 дней</li>
                <li>Ограничение: 3 анализа на устройство</li>
              </ul>
              <h4 class="text-sm font-semibold text-[#1b1b1d] mt-4 mb-2">Способ получения:</h4>
              <p class="text-sm text-[#44474d]">Результат доступен на сайте сразу после завершения анализа (5–10 минут).</p>
            </div>

            <!-- Платный -->
            <div class="bg-white border-2 border-[#006a62] rounded-xl p-6 relative">
              <div class="text-xs font-semibold text-[#006a62] bg-[#57fae9]/20 px-3 py-1 rounded-full w-fit mb-4">ПОЛНЫЙ ДОСТУП</div>
              <h3 class="text-lg font-semibold text-[#1b1b1d] mb-2">Полный отчёт</h3>
              <p class="text-2xl font-bold text-[#1b1b1d] mb-4">1 490 ₽</p>
              <p class="text-sm text-[#44474d] mb-4">Детальный аналитический отчёт для принятия бизнес-решений.</p>
              <h4 class="text-sm font-semibold text-[#1b1b1d] mb-2">Характеристики:</h4>
              <ul class="text-sm text-[#44474d] space-y-1.5 list-disc pl-5">
                <li>Все найденные ниши (без ограничений)</li>
                <li>Детальный анализ каждой ниши</li>
                <li>JTBD-анализ целевой аудитории</li>
                <li>Рекомендации по запуску (MVP-план)</li>
                <li>Оценка рисков</li>
                <li>Идеи позиционирования</li>
                <li>Ключевые поисковые запросы</li>
                <li>Оценка сложности входа на рынок</li>
                <li>Рыночные тренды</li>
                <li>Период анализа: 14 или 30 дней</li>
              </ul>
              <h4 class="text-sm font-semibold text-[#1b1b1d] mt-4 mb-2">Способ получения:</h4>
              <p class="text-sm text-[#44474d]">После оплаты полный отчёт доступен по уникальной ссылке на сайте. Ссылка действует бессрочно.</p>
            </div>
          </div>
        </section>

        <!-- Способ оплаты -->
        <section class="bg-white border border-[#c6c6cd] rounded-xl p-8">
          <h2 class="text-xl font-semibold text-[#1b1b1d] mb-4">Способ оплаты</h2>
          <p class="text-base text-[#44474d] leading-relaxed">
            Оплата производится онлайн через платёжный сервис Робокасса. 
            Доступные способы: банковская карта (Visa, MasterCard, МИР), СБП, электронные кошельки. 
            Чек формируется автоматически и направляется на email покупателя в соответствии с ФЗ-54.
          </p>
        </section>

        <!-- Возврат -->
        <section class="bg-white border border-[#c6c6cd] rounded-xl p-8">
          <h2 class="text-xl font-semibold text-[#1b1b1d] mb-4">Условия возврата</h2>
          <p class="text-base text-[#44474d] leading-relaxed mb-3">
            Возврат денежных средств возможен в случае технической невозможности предоставления услуги 
            (сбой генерации отчёта, ошибка системы).
          </p>
          <p class="text-base text-[#44474d] leading-relaxed mb-3">
            Для возврата необходимо направить заявку на email <strong>nikmaltcev@vk.com</strong> 
            с указанием причины возврата в течение 7 (семи) календарных дней с момента оплаты.
          </p>
          <p class="text-base text-[#44474d] leading-relaxed">
            Возврат не производится, если полный отчёт был успешно сгенерирован и предоставлен покупателю.
          </p>
        </section>

        <!-- Реквизиты -->
        <section class="bg-white border border-[#c6c6cd] rounded-xl p-8">
          <h2 class="text-xl font-semibold text-[#1b1b1d] mb-4">Реквизиты продавца</h2>
          <div class="text-base text-[#44474d] space-y-1">
            <p><strong>Мальцев Никита Евгеньевич</strong></p>
            <p>Самозанятый, применяющий налог на профессиональный доход (НПД)</p>
            <p>ИНН: 165924805367</p>
            <p>Телефон: +7 900 324-21-25</p>
            <p>Email: nikmaltcev@vk.com</p>
          </div>
        </section>

      </div>
    </main>
  </div>
</template>
