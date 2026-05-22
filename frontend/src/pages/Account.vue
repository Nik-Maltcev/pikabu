<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const user = ref<{ id: number; email: string } | null>(null)
const reports = ref<any[]>([])
const loading = ref(true)
const error = ref('')

// Auth state
const showLogin = ref(false)
const isRegister = ref(false)
const email = ref('')
const password = ref('')
const authLoading = ref(false)
const authError = ref('')

const apiBase = import.meta.env.VITE_API_URL || '/api'

function getToken(): string | null {
  return localStorage.getItem('bizmap_token')
}

function setToken(token: string) {
  localStorage.setItem('bizmap_token', token)
}

function logout() {
  localStorage.removeItem('bizmap_token')
  user.value = null
  reports.value = []
  showLogin.value = true
}

async function loadProfile() {
  const token = getToken()
  if (!token) {
    showLogin.value = true
    loading.value = false
    return
  }

  try {
    const res = await fetch(`${apiBase}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.status === 401) {
      localStorage.removeItem('bizmap_token')
      showLogin.value = true
      loading.value = false
      return
    }
    const data = await res.json()
    user.value = data.user
    reports.value = data.reports || []
  } catch (e: any) {
    error.value = 'Не удалось загрузить профиль'
  } finally {
    loading.value = false
  }
}

async function onSubmit() {
  authLoading.value = true
  authError.value = ''
  try {
    const endpoint = isRegister.value ? '/auth/register' : '/auth/login'
    const res = await fetch(`${apiBase}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value.trim(), password: password.value }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Ошибка')
    setToken(data.token)
    user.value = data.user
    showLogin.value = false
    await loadProfile()
  } catch (e: any) {
    authError.value = e.message || 'Ошибка'
  } finally {
    authLoading.value = false
  }
}

function goToReport(topicId: number, reportId: number) {
  router.push({ name: 'report', params: { topicId: String(topicId), reportId: String(reportId) } })
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(loadProfile)
</script>

<template>
  <div class="acc-page">
    <!-- Navbar -->
    <nav class="acc-nav">
      <router-link to="/" class="acc-brand">BizMap</router-link>
      <div v-if="user" class="acc-user-info">
        <span class="acc-email">{{ user.email }}</span>
        <button class="acc-logout" @click="logout">Выйти</button>
      </div>
    </nav>

    <!-- Loading -->
    <div v-if="loading" class="acc-center">
      <div class="acc-spinner"></div>
    </div>

    <!-- Login/Register -->
    <div v-else-if="showLogin" class="acc-center">
      <div class="acc-login-card">
        <h1 class="acc-login-title">{{ isRegister ? 'Регистрация' : 'Вход' }}</h1>
        <p class="acc-login-desc">{{ isRegister ? 'Создайте аккаунт для сохранения отчётов' : 'Войдите чтобы увидеть свои отчёты' }}</p>

        <input
          v-model="email"
          type="email"
          class="acc-input"
          placeholder="Email"
          @keyup.enter="onSubmit"
        />
        <input
          v-model="password"
          type="password"
          class="acc-input"
          placeholder="Пароль"
          @keyup.enter="onSubmit"
        />
        <button class="acc-btn" :disabled="authLoading || !email || !password" @click="onSubmit">
          {{ authLoading ? 'Загрузка...' : isRegister ? 'Зарегистрироваться' : 'Войти' }}
        </button>

        <button class="acc-link" @click="isRegister = !isRegister">
          {{ isRegister ? 'Уже есть аккаунт? Войти' : 'Нет аккаунта? Зарегистрироваться' }}
        </button>

        <p v-if="authError" class="acc-error">{{ authError }}</p>
      </div>
    </div>

    <!-- Profile -->
    <div v-else class="acc-content">
      <h1 class="acc-title">Мои отчёты</h1>

      <div v-if="reports.length === 0" class="acc-empty">
        <p>У вас пока нет отчётов.</p>
        <router-link to="/app" class="acc-btn">Начать анализ</router-link>
      </div>

      <div v-else class="acc-reports">
        <div
          v-for="r in reports"
          :key="r.id"
          class="acc-report-card"
          @click="goToReport(r.topic_id, r.id)"
        >
          <div class="acc-report-info">
            <span class="acc-report-mode">{{ r.analysis_mode === 'niche_search' ? '🔍 Поиск ниши' : '📊 Анализ' }}</span>
            <span class="acc-report-date">{{ formatDate(r.generated_at) }}</span>
          </div>
          <span class="acc-report-arrow">→</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.acc-page { min-height: 100vh; background: #f8f9fa; font-family: 'Inter', system-ui, sans-serif; }
.acc-nav { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; background: #fff; border-bottom: 1px solid #e5e5e5; }
.acc-brand { font-size: 18px; font-weight: 700; color: #1b1b1d; text-decoration: none; }
.acc-user-info { display: flex; align-items: center; gap: 12px; }
.acc-email { font-size: 14px; color: #6b7280; }
.acc-logout { font-size: 13px; color: #dc2626; background: none; border: none; cursor: pointer; }
.acc-center { display: flex; align-items: center; justify-content: center; min-height: 80vh; padding: 24px; }
.acc-spinner { width: 32px; height: 32px; border: 3px solid #e5e5e5; border-top-color: #006a62; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.acc-login-card { background: #fff; border: 1px solid #e5e5e5; border-radius: 16px; padding: 40px 32px; max-width: 400px; width: 100%; text-align: center; box-shadow: 0 4px 24px rgba(0,0,0,0.04); }
.acc-login-title { font-size: 24px; font-weight: 700; margin: 0 0 8px; color: #1b1b1d; }
.acc-login-desc { font-size: 14px; color: #6b7280; margin: 0 0 24px; }
.acc-input { width: 100%; padding: 14px 16px; border: 1px solid #e5e5e5; border-radius: 10px; font-size: 16px; margin-bottom: 12px; outline: none; font-family: inherit; }
.acc-input:focus { border-color: #006a62; }
.acc-btn { display: block; width: 100%; padding: 14px; border: none; border-radius: 10px; background: #006a62; color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; font-family: inherit; margin-bottom: 8px; }
.acc-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.acc-btn:hover:not(:disabled) { opacity: 0.9; }
.acc-link { font-size: 13px; color: #006a62; background: none; border: none; cursor: pointer; margin-top: 8px; }
.acc-error { font-size: 13px; color: #dc2626; margin-top: 12px; }

.acc-content { max-width: 600px; margin: 0 auto; padding: 40px 24px; }
.acc-title { font-size: 24px; font-weight: 700; margin: 0 0 24px; color: #1b1b1d; }
.acc-empty { text-align: center; padding: 40px; color: #6b7280; }
.acc-empty .acc-btn { display: inline-block; width: auto; padding: 12px 24px; margin-top: 16px; text-decoration: none; }
.acc-reports { display: flex; flex-direction: column; gap: 8px; }
.acc-report-card { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; background: #fff; border: 1px solid #e5e5e5; border-radius: 10px; cursor: pointer; transition: border-color 0.15s; }
.acc-report-card:hover { border-color: #006a62; }
.acc-report-info { display: flex; flex-direction: column; gap: 4px; }
.acc-report-mode { font-size: 15px; font-weight: 500; color: #1b1b1d; }
.acc-report-date { font-size: 13px; color: #6b7280; }
.acc-report-arrow { font-size: 18px; color: #9ca3af; }
</style>
