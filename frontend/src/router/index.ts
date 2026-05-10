import { createRouter, createWebHistory } from 'vue-router'
import Landing from '../pages/Landing.vue'
import TopicSelector from '../pages/TopicSelector.vue'
import AnalysisProgress from '../pages/AnalysisProgress.vue'
import ReportHistory from '../pages/ReportHistory.vue'
import ReportView from '../pages/ReportView.vue'
import Privacy from '../pages/Privacy.vue'
import Terms from '../pages/Terms.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'landing', component: Landing },
    { path: '/app', name: 'topics', component: TopicSelector },
    { path: '/analysis/:taskId', name: 'analysis', component: AnalysisProgress },
    { path: '/reports/:topicId', name: 'reports', component: ReportHistory },
    { path: '/reports/:topicId/:reportId', name: 'report', component: ReportView },
    { path: '/privacy', name: 'privacy', component: Privacy },
    { path: '/terms', name: 'terms', component: Terms },
    { path: '/pricing', name: 'pricing', component: () => import('../pages/Pricing.vue') },
    { path: '/account', name: 'account', component: () => import('../pages/Account.vue') },
  ],
})

export default router
