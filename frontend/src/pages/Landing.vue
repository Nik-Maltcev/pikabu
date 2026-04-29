<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

function goToApp() {
  router.push({ name: 'topics' })
}
</script>

<template>
  <div class="landing">
    <!-- Navbar -->
    <nav class="navbar">
      <div class="nav-container">
        <span class="nav-brand">NicheFind AI</span>
        <div class="nav-links">
          <a class="nav-link nav-link--active">Поиск ниш</a>
          <a class="nav-link">Тарифы</a>
        </div>
        <button class="nav-cta" @click="goToApp">Войти</button>
      </div>
    </nav>

    <!-- Hero -->
    <section class="hero">
      <h1 class="hero-title">
        Найдите прибыльную нишу для<br/>вашего бизнеса за 5 минут<br/>с помощью ИИ
      </h1>
      <p class="hero-desc">
        Мощный алгоритм анализирует тысячи трендов, поисковых запросов и данных конкурентов, чтобы выдать вам готовый план действий.
      </p>
      <button class="hero-btn" @click="goToApp">Начать поиск</button>

      <!-- Dashboard mockup -->
      <div class="hero-visual">
        <div class="visual-card">
          <div class="visual-bar"></div>
          <div class="visual-bar visual-bar--short"></div>
          <div class="visual-bar visual-bar--med"></div>
          <div class="visual-dots">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </section>

    <!-- How it works -->
    <section class="section">
      <div class="container">
        <h2 class="section-title">Как это работает</h2>
        <div class="steps-grid">
          <div class="step-card">
            <div class="step-icon">📊</div>
            <h3>Сбор данных</h3>
            <p>Мы агрегируем данные из сотен источников: поисковые тренды, соцсети, маркетплейсы и открытые базы данных.</p>
          </div>
          <div class="step-card">
            <div class="step-icon">🧠</div>
            <h3>ИИ-анализ</h3>
            <p>Наша нейросеть оценивает конкуренцию, потенциальный спрос, маржинальность и риски для каждой ниши.</p>
          </div>
          <div class="step-card">
            <div class="step-icon">📄</div>
            <h3>Готовый отчёт</h3>
            <p>Вы получите структурированный отчёт с рекомендациями, целевой аудиторией и планом запуска.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Benefits -->
    <section class="section section--gray">
      <div class="container">
        <h2 class="section-title">Преимущества для старта</h2>
        <div class="benefits-grid">
          <div class="benefit-card benefit-card--large">
            <div class="benefit-icon">⏱️</div>
            <h4>Экономия времени</h4>
            <p>Вместо недель ручного ресёрча вы получаете результат за минуты. Фокусируйтесь на продукте, а не на поиске данных.</p>
            <div class="benefit-tags">
              <span class="btag">Быстро</span>
              <span class="btag">Точно</span>
            </div>
          </div>
          <div class="benefit-card benefit-card--large">
            <div class="benefit-icon">🛡️</div>
            <h4>Снижение рисков</h4>
            <p>Объективная оценка на основе данных, а не интуиции. Узнайте реальный спрос до вложений.</p>
          </div>
          <div class="benefit-card">
            <div class="benefit-icon">📈</div>
            <h4>Глубокая аналитика</h4>
          </div>
          <div class="benefit-card">
            <div class="benefit-icon">🔄</div>
            <h4>Свежие тренды</h4>
          </div>
        </div>
      </div>
    </section>

    <!-- CTA -->
    <section class="section cta-section">
      <div class="container cta-block">
        <h2>Готовы найти свою нишу?</h2>
        <p>Первые результаты — бесплатно. Без регистрации.</p>
        <button class="hero-btn" @click="goToApp">Начать поиск ниши</button>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-container">
        <span class="footer-copy">© 2025 NicheFind AI. Профессиональная аналитика бизнес-ниш.</span>
        <span class="footer-brand">NicheFind AI</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  min-height: 100vh;
  background: #fff;
}

/* Navbar */
.navbar {
  background: #fff;
  border-bottom: 1px solid #eee;
  padding: 0 24px;
  height: 56px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
}

.nav-brand {
  font-size: 18px;
  font-weight: 700;
  color: #111;
  letter-spacing: -0.5px;
  margin-right: 32px;
}

.nav-links {
  display: flex;
  gap: 24px;
  flex: 1;
}

.nav-link {
  font-size: 14px;
  color: #666;
  text-decoration: none;
  cursor: pointer;
}

.nav-link--active {
  color: #00bfa5;
  font-weight: 500;
}

.nav-cta {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background: #111;
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
}

/* Hero */
.hero {
  text-align: center;
  padding: 80px 24px 60px;
  background: linear-gradient(180deg, #f0fdf9 0%, #fff 100%);
}

.hero-title {
  font-size: 44px;
  font-weight: 700;
  color: #111;
  line-height: 1.2;
  margin: 0 0 20px;
  letter-spacing: -1px;
}

.hero-desc {
  font-size: 16px;
  color: #666;
  max-width: 560px;
  margin: 0 auto 32px;
  line-height: 1.6;
}

.hero-btn {
  display: inline-flex;
  align-items: center;
  padding: 14px 32px;
  border: none;
  border-radius: 10px;
  background: #00bfa5;
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: opacity 0.15s;
}

.hero-btn:hover {
  opacity: 0.9;
}

/* Visual mockup */
.hero-visual {
  margin-top: 48px;
  display: flex;
  justify-content: center;
}

.visual-card {
  width: 480px;
  max-width: 100%;
  padding: 32px;
  background: #1a1a2e;
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.visual-bar {
  height: 12px;
  background: linear-gradient(90deg, #00bfa5, #00e5cc);
  border-radius: 6px;
  width: 100%;
}

.visual-bar--short {
  width: 60%;
  background: linear-gradient(90deg, #4fc3f7, #00bfa5);
}

.visual-bar--med {
  width: 80%;
  background: linear-gradient(90deg, #00bfa5, #69f0ae);
}

.visual-dots {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.visual-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #00bfa5;
  opacity: 0.6;
}

.visual-dots span:nth-child(2) { opacity: 0.8; }
.visual-dots span:nth-child(3) { opacity: 1; }
.visual-dots span:nth-child(4) { opacity: 0.7; }
.visual-dots span:nth-child(5) { opacity: 0.5; }

/* Sections */
.section {
  padding: 80px 24px;
}

.section--gray {
  background: #f8f9fa;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
}

.section-title {
  font-size: 28px;
  font-weight: 700;
  color: #111;
  margin: 0 0 40px;
  text-align: center;
}

/* Steps */
.steps-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.step-card {
  text-align: center;
  padding: 32px 24px;
  background: #f8f9fa;
  border-radius: 16px;
}

.step-icon {
  font-size: 32px;
  margin-bottom: 16px;
}

.step-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: #111;
  margin: 0 0 8px;
}

.step-card p {
  font-size: 13px;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

/* Benefits */
.benefits-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.benefit-card {
  padding: 28px;
  border: 1px solid #eee;
  border-radius: 14px;
  background: #fff;
}

.benefit-card--large {
  grid-column: span 1;
}

.benefit-icon {
  font-size: 24px;
  margin-bottom: 12px;
}

.benefit-card h4 {
  font-size: 16px;
  font-weight: 600;
  color: #111;
  margin: 0 0 8px;
}

.benefit-card p {
  font-size: 13px;
  color: #666;
  margin: 0;
  line-height: 1.5;
}

.benefit-tags {
  display: flex;
  gap: 6px;
  margin-top: 16px;
}

.btag {
  padding: 4px 10px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 12px;
  color: #555;
}

/* CTA */
.cta-section {
  background: #fff;
}

.cta-block {
  text-align: center;
}

.cta-block h2 {
  font-size: 32px;
  font-weight: 700;
  color: #111;
  margin: 0 0 12px;
}

.cta-block p {
  font-size: 15px;
  color: #666;
  margin: 0 0 28px;
}

/* Footer */
.footer {
  padding: 20px 24px;
  border-top: 1px solid #eee;
}

.footer-container {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-copy {
  font-size: 13px;
  color: #999;
}

.footer-brand {
  font-size: 14px;
  font-weight: 700;
  color: #111;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
  }

  .steps-grid {
    grid-template-columns: 1fr;
  }

  .benefits-grid {
    grid-template-columns: 1fr;
  }

  .section {
    padding: 48px 24px;
  }

  .nav-links {
    display: none;
  }
}
</style>
