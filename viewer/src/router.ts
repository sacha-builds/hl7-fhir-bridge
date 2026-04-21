import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'inbox',
    component: () => import('@/views/InboxView.vue'),
  },
  {
    path: '/messages/:id',
    name: 'message',
    component: () => import('@/views/MessageDetailView.vue'),
    props: true,
  },
  {
    path: '/patients',
    name: 'patients',
    component: () => import('@/views/PatientsView.vue'),
  },
  {
    path: '/metrics',
    name: 'metrics',
    component: () => import('@/views/MetricsView.vue'),
  },
  {
    path: '/patients/:id',
    name: 'patient',
    component: () => import('@/views/PatientChartView.vue'),
    props: true,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
