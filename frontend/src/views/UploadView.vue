<template>
  <div class="upload-page">
    <div class="card upload-card">
      <h1>Análisis de tráfico difuso</h1>
      <p class="subtitle">Sube un CSV de sensor para generar automáticamente el informe.</p>

      <!-- Drop zone -->
      <div
        class="drop-zone"
        :class="{ 'drag-over': isDragging, 'has-file': file }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
        @click="fileInput.click()"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".csv"
          class="hidden-input"
          @change="onFileChange"
        />
        <template v-if="!file">
          <span class="drop-icon">📂</span>
          <p class="drop-text">Arrastra un CSV aquí o <strong>haz clic</strong> para seleccionar</p>
          <p class="drop-hint">Solo ficheros .csv</p>
        </template>
        <template v-else>
          <span class="drop-icon">✅</span>
          <p class="drop-text file-name">{{ file.name }}</p>
          <p class="drop-hint">{{ formatBytes(file.size) }} · Haz clic para cambiar</p>
        </template>
      </div>

      <!-- Advanced params -->
      <div class="params-section">
        <button class="params-toggle" @click="showParams = !showParams">
          <span>⚙️ Parámetros avanzados</span>
          <span class="arrow" :class="{ open: showParams }">▸</span>
        </button>

        <Transition name="slide">
          <div v-show="showParams" class="params-grid">
            <label class="param-item">
              <span class="param-label">MIN_LIFT</span>
              <span class="param-desc">Lift mínimo de las reglas</span>
              <input v-model.number="params.min_lift" type="number" step="0.1" min="1" />
            </label>
            <label class="param-item">
              <span class="param-label">MIN_CONFIANZA</span>
              <span class="param-desc">Confianza mínima (0–1)</span>
              <input v-model.number="params.min_confianza" type="number" step="0.05" min="0" max="1" />
            </label>
            <label class="param-item">
              <span class="param-label">MIN_SOPORTE</span>
              <span class="param-desc">Soporte difuso mínimo</span>
              <input v-model.number="params.min_soporte" type="number" step="0.001" min="0" />
            </label>
            <label class="param-item">
              <span class="param-label">BEAM_WIDTH</span>
              <span class="param-desc">Anchura del beam search</span>
              <input v-model.number="params.beam_width" type="number" step="1" min="1" />
            </label>
            <label class="param-item">
              <span class="param-label">MAX_VARS</span>
              <span class="param-desc">Profundidad máxima del beam</span>
              <input v-model.number="params.max_vars" type="number" step="1" min="1" max="5" />
            </label>
            <label class="param-item">
              <span class="param-label">TOL_HORAS</span>
              <span class="param-desc">Tolerancia rampa horas (0–1)</span>
              <input v-model.number="params.tol_horas" type="number" step="0.05" min="0" max="1" />
            </label>
          </div>
        </Transition>
      </div>

      <!-- Error -->
      <p v-if="error" class="error-msg">{{ error }}</p>

      <!-- Submit -->
      <button
        class="btn btn-primary submit-btn"
        :disabled="!file || loading"
        @click="submit"
      >
        <span v-if="loading">⏳ Enviando…</span>
        <span v-else>🚀 Ejecutar pipeline</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useJobStore } from '../stores/job.js'
import { runPipeline } from '../api/pipeline.js'

const router   = useRouter()
const jobStore = useJobStore()

const file      = ref(null)
const fileInput = ref(null)
const isDragging = ref(false)
const showParams = ref(false)
const loading   = ref(false)
const error     = ref(null)

const params = reactive({
  min_lift:      1.5,
  min_confianza: 0.5,
  min_soporte:   0.005,
  beam_width:    10,
  max_vars:      3,
  tol_horas:     0.5,
})

function onFileChange(e) {
  const f = e.target.files[0]
  if (f) setFile(f)
}

function onDrop(e) {
  isDragging.value = false
  const f = e.dataTransfer.files[0]
  if (f && f.name.endsWith('.csv')) setFile(f)
  else error.value = 'Solo se admiten ficheros .csv'
}

function setFile(f) {
  file.value  = f
  error.value = null
}

function formatBytes(n) {
  if (n < 1024) return n + ' B'
  if (n < 1048576) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1048576).toFixed(1) + ' MB'
}

async function submit() {
  if (!file.value || loading.value) return
  loading.value = true
  error.value   = null

  const fd = new FormData()
  fd.append('file', file.value)
  Object.entries(params).forEach(([k, v]) => fd.append(k, v))

  try {
    const { data } = await runPipeline(fd)
    jobStore.setJob(data.job_id)
    router.push({ name: 'status', params: { jobId: data.job_id } })
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Error al conectar con el servidor.'
    loading.value = false
  }
}
</script>

<style scoped>
.upload-page { display: flex; justify-content: center; padding: 1rem 0; }
.upload-card { max-width: 700px; width: 100%; }

h1 { font-size: 1.6rem; font-weight: 800; color: #1a1a2e; margin-bottom: .4rem; }
.subtitle { color: #6b7280; margin-bottom: 1.8rem; }

/* Drop zone */
.drop-zone {
  border: 2.5px dashed #cbd5e1;
  border-radius: 12px;
  padding: 2.5rem 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: border-color .2s, background .2s;
  margin-bottom: 1.5rem;
}
.drop-zone:hover, .drag-over {
  border-color: #2563eb;
  background: #eff6ff;
}
.has-file { border-color: #059669; background: #f0fdf4; }
.drop-icon { font-size: 2.5rem; display: block; margin-bottom: .6rem; }
.drop-text { font-size: 1rem; color: #374151; }
.file-name { font-weight: 700; color: #1a1a2e; word-break: break-all; }
.drop-hint { font-size: .8rem; color: #9ca3af; margin-top: .3rem; }
.hidden-input { display: none; }

/* Params panel */
.params-section { margin-bottom: 1.5rem; }
.params-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: #f1f5f9;
  border: none;
  border-radius: 8px;
  padding: .7rem 1rem;
  font-size: .9rem;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
}
.params-toggle:hover { background: #e2e8f0; }
.arrow { transition: transform .2s; display: inline-block; }
.arrow.open { transform: rotate(90deg); }

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  padding: 1rem 0 .5rem;
}
.param-item {
  display: flex;
  flex-direction: column;
  gap: .25rem;
}
.param-label { font-size: .78rem; font-weight: 700; color: #4b5563; font-family: monospace; }
.param-desc  { font-size: .72rem; color: #9ca3af; }
.param-item input {
  padding: .4rem .6rem;
  border: 1.5px solid #d1d5db;
  border-radius: 6px;
  font-size: .9rem;
  outline: none;
  width: 100%;
}
.param-item input:focus { border-color: #2563eb; }

/* Transitions */
.slide-enter-active, .slide-leave-active { transition: opacity .2s, transform .2s; }
.slide-enter-from, .slide-leave-to { opacity: 0; transform: translateY(-6px); }

.error-msg { color: #dc2626; font-size: .9rem; margin-bottom: .8rem; }
.submit-btn { width: 100%; justify-content: center; padding: .8rem; font-size: 1rem; }
</style>
