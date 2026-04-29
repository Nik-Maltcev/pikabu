<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goToApp() {
  router.push({ name: 'topics' })
}
</script>

<template>
  <div class="landing">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-container">
        <div class="hero-badge">AI-аналитика ниш</div>
        <h1 class="hero-title">
          Найдите прибыльную нишу<br/>
          <span class="hero-highlight">до того, как вложите деньги</span>
        </h1>
        <p class="hero-desc">
          Сервис анализирует тысячи обсуждений реальных людей и находит ниши, 
          где есть спрос, но мало конкурентов. Без догадок — только данные.
        </p>
        <div class="hero-actions">
          <button class="btn-primary" @click="goToApp">
            Найти нишу бесплатно
          </button>
          <span class="hero-hint">Первые 3–5 ниш — бесплатно</span>
        </div>

        <div class="hero-stats">
          <div class="stat">
            <span class="stat-value">10 000+</span>
            <span class="stat-label">обсуждений анализируется</span>
          </div>
          <div class="stat">
            <span class="stat-value">3 платформы</span>
            <span class="stat-label">Pikabu · Habr · VC.ru</span>
          </div>
          <div class="stat">
            <span class="stat-value">~5 мин</span>
            <span class="stat-label">до первых результатов</span>
          </div>
        </div>
      </div>
    </section>

    <!-- Problem -->
    <section class="section problem">
      <div class="container">
        <h2 class="section-title">Знакомо?</h2>
        <div class="problem-grid">
          <div class="problem-card">
            <div class="problem-icon">🤔</div>
            <p>Хочу начать бизнес, но не знаю какую нишу выбрать</p>
          </div>
          <div class="problem-card">
            <div class="problem-icon">📊</div>
            <p>Гуглю часами, но не понимаю — есть ли реальный спрос</p>
          </div>
          <div class="problem-card">
            <div class="problem-icon">💸</div>
            <p>Боюсь вложить деньги в идею, которая никому не нужна</p>
          </div>
          <div class="problem-card">
            <div class="problem-icon">🏃</div>
            <p>Конкуренты уже заняли всё — или мне так кажется?</p>
          </div>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="section how">
      <div class="container">
        <h2 class="section-title">Как это работает</h2>
        <div class="steps">
          <div class="step">
            <div class="step-num">1</div>
            <h3>Выберите категорию</h3>
            <p>Маркетинг, IT, еда, путешествия — выберите то, что вам интересно. Или просто посмотрите все.</p>
          </div>
          <div class="step-arrow">→</div>
          <div class="step">
            <div class="step-num">2</div>
            <h3>AI анализирует данные</h3>
            <p>Система собирает тысячи постов и комментариев, находит боли людей, незакрытые потребности и тренды.</p>
          </div>
          <div class="step-arrow">→</div>
          <div class="step">
            <div class="step-num">3</div>
            <h3>Получите ниши</h3>
            <p>Готовый список ниш с оценкой спроса, конкуренции и конкретными идеями для запуска.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- What you get -->
    <section class="section value">
      <div class="container">
        <h2 class="section-title">Что вы получите</h2>
        <div class="value-grid">
          <div class="value-col value-col--free">
            <div class="value-badge value-badge--free">Бесплатно</div>
            <h3>Превью отчёта</h3>
            <ul class="value-list">
              <li class="value-item value-item--included">3–5 лучших ниш</li>
              <li class="value-item value-item--included">Краткий потенциал каждой</li>
              <li class="value-item value-item--included">Уровень спроса</li>
              <li class="value-item value-item--locked">Полный список ниш</li>
              <li class="value-item value-item--locked">Подробный анализ</li>
              <li class="value-item value-item--locked">Рекомендации по запуску</li>
              <li class="value-item value-item--locked">Оценка рисков</li>
              <li class="value-item value-item--locked">Поисковые запросы</li>
            </ul>
          </div>
          <div class="value-col value-col--paid">
            <div class="value-badge value-badge--paid">Полный отчёт</div>
            <h3>Всё для старта</h3>
            <ul class="value-list">
              <li class="value-item value-item--included">Все найденные ниши</li>
              <li class="value-item value-item--included">Детальный анализ каждой</li>
              <li class="value-item value-item--included">JTBD-анализ аудитории</li>
              <li class="value-item value-item--included">Идеи позиционирования</li>
              <li class="value-item value-item--included">MVP-план запуска</li>
              <li class="value-item value-item--included">Оценка конкуренции</li>
              <li class="value-item value-item--included">Рыночные тренды</li>
              <li class="value-item value-item--included">Ключевые запросы</li>
            </ul>
            <div class="value-price">от 299 ₽</div>
          </div>
        </div>
      </div>
    </section>

    <!-- Social proof -->
    <section class="section proof">
      <div class="container">
        <h2 class="section-title">Почему это работает</h2>
        <div class="proof-grid">
          <div class="proof-card">
            <div class="proof-icon">💬</div>
            <h4>Реальные данные</h4>
            <p>Анализируем не абстрактные тренды, а конкретные жалобы и запросы живых людей на форумах.</p>
          </div>
          <div class="proof-card">
            <div class="proof-icon">🎯</div>
            <h4>Точечный анализ</h4>
            <p>AI выделяет боли, которые люди описывают своими словами — это и есть незакрытый спрос.</p>
          </div>
          <div class="proof-card">
            <div class="proof-icon">⚡</div>
            <h4>Быстро и дёшево</h4>
            <p>Вместо недель ручного ресёрча — готовый отчёт за 5 минут. Дешевле одного часа фрилансера.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="section cta">
      <div class="container cta-container">
        <h2 class="cta-title">Готовы найти свою нишу?</h2>
        <p class="cta-desc">Первые результаты — бесплатно. Без регистрации.</p>
        <button class="btn-primary btn-primary--lg" @click="goToApp">
          Начать поиск ниши
        </button>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="container footer-inner">
        <span class="footer-brand">NicheFind</span>
        <span class="footer-copy">© 2025</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ═══ Layout ═══ */
.landing {
  min-height: 100vh;
  overflow-x: hidden;
}

.container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
}

.section {
  padding: 80px 0;
}

.section-title {
  text-align: center;
  font-size: 32px;
  margin: 0 0 48px;
  color: var(--text-h);
}

/* ═══ Hero ═══ */
.hero {
  padding: 100px 0 80px;
  text-align: center;
  background: linear-gradient(180deg, var(--accent-bg) 0%, transparent 100%);
}

.hero-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 24px;
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: 20px;
  background: var(--accent-bg);
  border: 1px solid var(--accent-border);
  color: var(--accent);
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 24px;
}

.hero-title {
  font-size: 48px;
  line-height: 1.15;
  margin: 0 0 20px;
  font-weight: 600;
  color: var(--text-h);
}

.hero-highlight {
  background: linear-gradient(135deg, var(--accent), #7c3aed);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-desc {
  font-size: 18px;
  line-height: 1.6;
  color: var(--text);
  margin: 0 0 32px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.hero-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 48px;
}

.hero-hint {
  font-size: 13px;
  color: var(--text);
}

.hero-stats {
  display: flex;
  justify-content: center;
  gap: 48px;
  padding-top: 32px;
  border-top: 1px solid var(--border);
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-h);
}

.stat-label {
  font-size: 13px;
  color: var(--text);
}

/* ═══ Buttons ═══ */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 14px 32px;
  border: none;
  border-radius: 10px;
  background: var(--accent);
  color: #fff;
  font-size: 16px;
  font-weight: 500;
  font-family: var(--sans);
  cursor: pointer;
  transition: transform 0.15s, opacity 0.15s;
}

.btn-primary:hover {
  transform: translateY(-1px);
  opacity: 0.9;
}

.btn-primary--lg {
  padding: 18px 40px;
  font-size: 18px;
}

/* ═══ Problem ═══ */
.problem {
  background: var(--bg);
}

.problem-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.problem-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  border: 1px solid var(--border);
  border-radius: 12px;
  transition: border-color 0.2s;
}

.problem-card:hover {
  border-color: var(--accent-border);
}

.problem-icon {
  font-size: 28px;
  flex-shrink: 0;
}

.problem-card p {
  margin: 0;
  font-size: 15px;
  color: var(--text-h);
  line-height: 1.5;
}

/* ═══ How it works ═══ */
.how {
  background: var(--accent-bg);
}

.steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 24px;
}

.step {
  flex: 1;
  max-width: 280px;
  text-align: center;
}

.step-num {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--accent);
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.step h3 {
  font-size: 18px;
  margin: 0 0 8px;
  color: var(--text-h);
}

.step p {
  font-size: 14px;
  color: var(--text);
  margin: 0;
  line-height: 1.5;
}

.step-arrow {
  font-size: 24px;
  color: var(--accent);
  margin-top: 12px;
  flex-shrink: 0;
}

/* ═══ Value / Pricing ═══ */
.value-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.value-col {
  padding: 32px;
  border-radius: 16px;
  border: 1px solid var(--border);
}

.value-col--paid {
  border-color: var(--accent-border);
  background: var(--accent-bg);
  position: relative;
}

.value-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.value-badge--free {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}

.value-badge--paid {
  background: var(--accent-bg);
  color: var(--accent);
}

.value-col h3 {
  font-size: 20px;
  margin: 0 0 16px;
  color: var(--text-h);
}

.value-list {
  list-style: none;
  padding: 0;
  margin: 0 0 20px;
}

.value-item {
  padding: 8px 0;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.value-item::before {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 11px;
}

.value-item--included {
  color: var(--text-h);
}

.value-item--included::before {
  content: '✓';
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}

.value-item--locked {
  color: var(--text);
  opacity: 0.6;
}

.value-item--locked::before {
  content: '🔒';
  background: transparent;
}

.value-price {
  font-size: 28px;
  font-weight: 600;
  color: var(--accent);
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

/* ═══ Proof ═══ */
.proof-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.proof-card {
  text-align: center;
  padding: 32px 24px;
  border: 1px solid var(--border);
  border-radius: 12px;
}

.proof-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.proof-card h4 {
  font-size: 16px;
  margin: 0 0 8px;
  color: var(--text-h);
}

.proof-card p {
  font-size: 14px;
  color: var(--text);
  margin: 0;
  line-height: 1.5;
}

/* ═══ CTA ═══ */
.cta {
  background: linear-gradient(180deg, transparent 0%, var(--accent-bg) 100%);
}

.cta-container {
  text-align: center;
}

.cta-title {
  font-size: 36px;
  margin: 0 0 12px;
  color: var(--text-h);
}

.cta-desc {
  font-size: 16px;
  color: var(--text);
  margin: 0 0 32px;
}

/* ═══ Footer ═══ */
.footer {
  padding: 24px 0;
  border-top: 1px solid var(--border);
}

.footer-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-brand {
  font-weight: 600;
  color: var(--text-h);
}

.footer-copy {
  font-size: 13px;
  color: var(--text);
}

/* ═══ Responsive ═══ */
@media (max-width: 768px) {
  .hero-title {
    font-size: 32px;
  }

  .hero-stats {
    flex-direction: column;
    gap: 16px;
  }

  .problem-grid {
    grid-template-columns: 1fr;
  }

  .steps {
    flex-direction: column;
    align-items: center;
  }

  .step-arrow {
    transform: rotate(90deg);
  }

  .value-grid {
    grid-template-columns: 1fr;
  }

  .proof-grid {
    grid-template-columns: 1fr;
  }

  .section {
    padding: 48px 0;
  }
}
</style>
