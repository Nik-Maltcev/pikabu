<script setup lang="ts">
</script>

<template>
  <div class="bg-[#fcf8fa] text-[#1b1b1d] min-h-screen flex flex-col font-['Inter']">
    <nav class="fixed top-0 w-full z-50 border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div class="flex justify-between items-center px-6 h-16 max-w-7xl mx-auto">
        <router-link to="/" class="text-xl font-bold tracking-tight text-slate-900 no-underline">BizNiche AI</router-link>
      </div>
    </nav>

    <main class="flex-grow pt-24 pb-16 px-6 max-w-3xl mx-auto w-full">
      <h1 class="text-3xl font-bold mb-8">Политика конфиденциальности</h1>
      <p class="text-sm text-[#76777d] mb-8">Дата вступления в силу: 1 мая 2025 г.</p>

      <div class="prose">
        <h2 class="text-xl font-semibold mt-8 mb-3">1. Общие положения</h2>
        <p>Настоящая Политика конфиденциальности определяет порядок обработки и защиты персональных данных пользователей сервиса BizNiche AI (далее — Сервис).</p>
        <p>Исполнитель: Мальцев Никита Евгеньевич, самозанятый (НПД), ИНН 165924805367.</p>

        <h2 class="text-xl font-semibold mt-8 mb-3">2. Какие данные мы собираем</h2>
        <p>Сервис собирает минимальный объём данных, необходимый для работы:</p>
        <ul class="list-disc pl-6 space-y-1">
          <li><strong>Технические данные</strong> — цифровой отпечаток браузера (fingerprint), IP-адрес, тип устройства. Используются для ограничения бесплатных анализов и защиты от злоупотреблений.</li>
          <li><strong>Данные об использовании</strong> — выбранные категории, параметры анализа. Используются для выполнения запроса.</li>
          <li><strong>Платёжные данные</strong> — обрабатываются исключительно платёжным провайдером (Робокасса). Мы не храним данные банковских карт.</li>
          <li><strong>Email</strong> — только если вы его указали для получения отчёта.</li>
        </ul>

        <h2 class="text-xl font-semibold mt-8 mb-3">3. Цели обработки данных</h2>
        <ul class="list-disc pl-6 space-y-1">
          <li>Предоставление услуг Сервиса (генерация отчётов)</li>
          <li>Ограничение бесплатного использования (rate limiting)</li>
          <li>Обработка платежей</li>
          <li>Улучшение качества Сервиса</li>
        </ul>

        <h2 class="text-xl font-semibold mt-8 mb-3">4. Хранение и защита данных</h2>
        <p>Данные хранятся на защищённых серверах. Мы не передаём персональные данные третьим лицам, за исключением случаев, предусмотренных законодательством РФ.</p>
        <p>Цифровые отпечатки хранятся в хешированном виде (SHA-256) и не позволяют идентифицировать конкретного пользователя.</p>

        <h2 class="text-xl font-semibold mt-8 mb-3">5. Cookies и аналитика</h2>
        <p>Сервис может использовать технические cookies для корректной работы. Мы не используем рекламные трекеры.</p>

        <h2 class="text-xl font-semibold mt-8 mb-3">6. Права пользователя</h2>
        <p>Вы имеете право запросить удаление ваших данных, написав на email, указанный в разделе «Контакты».</p>

        <h2 class="text-xl font-semibold mt-8 mb-3">7. Контакты</h2>
        <p>По вопросам обработки персональных данных: <strong>support@bizniche.ai</strong></p>
        <p>Мальцев Никита Евгеньевич, ИНН 165924805367</p>
      </div>
    </main>
  </div>
</template>
