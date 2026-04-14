import { createRouter, createWebHistory } from 'vue-router'
import TopicSelector from '../pages/TopicSelector.vue'
import AnalysisProgress from '../pages/AnalysisProgress.vue'
import ReportHistory from '../pages/ReportHistory.vue'
import ReportView from '../pages/ReportView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'topics', component: TopicSelector },
    { path: '/analysis/:taskId', name: 'analysis', component: AnalysisProgress },
    { path: '/reports/:topicId', name: 'reports', component: ReportHistory },
    { path: '/reports/:topicId/:reportId', name: 'report', component: ReportView },
  ],
})

export default router
