import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import StatusView from '../views/StatusView.vue'
import ReportView from '../views/ReportView.vue'

const routes = [
  { path: '/',               name: 'upload', component: UploadView },
  { path: '/status/:jobId',  name: 'status', component: StatusView },
  { path: '/report/:jobId',  name: 'report', component: ReportView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
