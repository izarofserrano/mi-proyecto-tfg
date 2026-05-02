<template>
  <div class="status-page">
    <div class="card status-card">
      <h2>Procesando pipeline</h2>
      <p class="job-id">Job ID: <code>{{ jobId }}</code></p>

      <!-- Progress bar -->
      <div class="progress-wrap">
        <div class="progress-bar" :style="{ width: progress + '%' }" :class="barClass" />
      </div>
      <div class="progress-labels">
        <span class="step-text">{{ step || '…' }}</span>
        <span class="pct-text">{{ progress }}%</span>
      </div>

      <!-- Status badge -->
      <div class="badge-row">
        <span class="badge" :class="'badge-' + status">{{ statusLabel }}</span>
        <span v-if="sensorId" class="meta-chip">Sensor: {{ sensorId }}</span>
        <span v-if="metrica"  class="meta-chip">Métrica: {{ metrica }}</span>
      </div>

      <!-- Error -->
      <div v-if="status === 'error'" class="error-box">
        <strong>Error durante el procesamiento:</strong>
        <pre>{{ errorMsg }}</pre>
        <RouterLink to="/" class="btn btn-secondary retry-btn">← Volver e intentar de nuevo</RouterLink>
      </div>

      <!-- Done (brief delay before redirect) -->
      <div v-if="status === 'done'" class="done-box">
        <span>✅ Completado — redirigiendo al informe…</span>
      </div>

      <!-- Cancel / back -->
      <RouterLink v-if="status !== 'done'" to="/" class="back-link">← Subir otro fichero</RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useJobStore } from '../stores/job.js'
import { getStatus } from '../api/pipeline.js'

const route    = useRoute()
const router   = useRouter()
const jobStore = useJobStore()

const jobId    = route.params.jobId
const status   = computed(() => jobStore.status  ?? 'pending')
const progress = computed(() => jobStore.progress ?? 0)
const step     = computed(() => jobStore.step)
const sensorId = computed(() => jobStore.sensorId)
const metrica  = computed(() => jobStore.metrica)
const errorMsg = computed(() => jobStore.errorMsg)

const barClass = computed(() => ({
  'bar-running': status.value === 'running',
  'bar-done':    status.value === 'done',
  'bar-error':   status.value === 'error',
}))

const statusLabel = computed(() => ({
  pending: 'En cola',
  running: 'Procesando',
  done:    'Completado',
  error:   'Error',
}[status.value] ?? status.value))

let timer = null

async function poll() {
  try {
    const { data } = await getStatus(jobId)
    jobStore.applyStatus(data)
    if (data.status === 'done') {
      clearInterval(timer)
      setTimeout(() => router.push({ name: 'report', params: { jobId } }), 800)
    }
    if (data.status === 'error') {
      clearInterval(timer)
    }
  } catch {
    // network hiccup — keep polling
  }
}

onMounted(() => {
  if (!jobStore.jobId) jobStore.setJob(jobId)
  poll()
  timer = setInterval(poll, 2000)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.status-page { display: flex; justify-content: center; padding: 1rem 0; }
.status-card { max-width: 620px; width: 100%; }

h2 { font-size: 1.4rem; font-weight: 800; margin-bottom: .3rem; }
.job-id { font-size: .8rem; color: #6b7280; margin-bottom: 1.6rem; }
.job-id code { background: #f3f4f6; padding: .15rem .4rem; border-radius: 4px; }

/* Progress */
.progress-wrap {
  height: 14px;
  background: #e5e7eb;
  border-radius: 9999px;
  overflow: hidden;
  margin-bottom: .5rem;
}
.progress-bar {
  height: 100%;
  border-radius: 9999px;
  background: #2563eb;
  transition: width .4s ease, background .3s;
}
.bar-running { background: #2563eb; animation: pulse-bar 1.8s ease-in-out infinite; }
.bar-done    { background: #059669; }
.bar-error   { background: #dc2626; }

@keyframes pulse-bar {
  0%, 100% { opacity: 1; }
  50%       { opacity: .7; }
}

.progress-labels {
  display: flex;
  justify-content: space-between;
  font-size: .85rem;
  color: #4b5563;
  margin-bottom: 1.4rem;
}
.step-text { font-style: italic; }
.pct-text  { font-weight: 700; }

/* Badge */
.badge-row { display: flex; align-items: center; flex-wrap: wrap; gap: .6rem; margin-bottom: 1.5rem; }
.badge {
  padding: .3rem .8rem;
  border-radius: 9999px;
  font-size: .8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
}
.badge-pending { background: #e5e7eb; color: #6b7280; }
.badge-running { background: #dbeafe; color: #1d4ed8; }
.badge-done    { background: #d1fae5; color: #047857; }
.badge-error   { background: #fee2e2; color: #b91c1c; }

.meta-chip {
  background: #f1f5f9;
  border-radius: 9999px;
  padding: .25rem .7rem;
  font-size: .8rem;
  color: #374151;
}

/* Error */
.error-box {
  background: #fef2f2;
  border: 1.5px solid #fca5a5;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
}
.error-box pre {
  margin-top: .5rem;
  font-size: .8rem;
  white-space: pre-wrap;
  color: #7f1d1d;
}
.retry-btn { margin-top: .8rem; font-size: .9rem; }

/* Done */
.done-box {
  background: #f0fdf4;
  border: 1.5px solid #6ee7b7;
  border-radius: 8px;
  padding: .8rem 1rem;
  color: #065f46;
  font-weight: 600;
  margin-bottom: 1rem;
}

.back-link { font-size: .85rem; color: #6b7280; text-decoration: none; }
.back-link:hover { color: #374151; }
</style>
