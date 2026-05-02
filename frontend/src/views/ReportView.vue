<template>
  <div class="report-page">
    <!-- Toolbar -->
    <div class="toolbar">
      <RouterLink to="/" class="btn btn-secondary">← Nuevo análisis</RouterLink>
      <div class="toolbar-center">
        <span v-if="sensorId" class="chip">Sensor: {{ sensorId }}</span>
        <span v-if="metrica"  class="chip">Métrica: {{ metrica }}</span>
      </div>
      <button class="btn btn-success" :disabled="!reportMd" @click="downloadReport">
        ⬇ Descargar informe
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <span class="spinner" />
      <p>Cargando informe…</p>
    </div>

    <!-- Error -->
    <div v-else-if="fetchError" class="error-box card">{{ fetchError }}</div>

    <!-- Main layout: report + rules sidebar -->
    <div v-else class="report-layout">

      <!-- Markdown report -->
      <article class="report-panel card">
        <div v-if="reportMd" class="markdown-body" v-html="parsedHtml" />
        <p v-else class="empty">El informe aún no está disponible.</p>
      </article>

      <!-- Rules sidebar -->
      <aside class="rules-panel card">
        <h3 class="rules-title">Reglas de asociación</h3>
        <p class="rules-meta">{{ rulesTotal }} reglas · página {{ rulesPage }}</p>

        <div v-if="rulesLoading" class="rules-loading"><span class="spinner" /></div>
        <div v-else-if="!rules.length" class="empty">Sin reglas disponibles.</div>

        <table v-else class="rules-table">
          <thead>
            <tr>
              <th @click="toggleSort('antecedente')">Antecedente <SortIcon col="antecedente" /></th>
              <th @click="toggleSort('consecuente')">Consecuente <SortIcon col="consecuente" /></th>
              <th @click="toggleSort('n_vars')" class="num">Vars</th>
              <th @click="toggleSort('soporte')" class="num">Sop.</th>
              <th @click="toggleSort('confianza')" class="num">Conf.</th>
              <th @click="toggleSort('lift')" class="num">Lift ▴</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in sortedRules" :key="r.antecedente + r.consecuente">
              <td class="ant-cell">{{ r.antecedente }}</td>
              <td><span class="badge-cons" :class="consClass(r.consecuente)">{{ r.consecuente }}</span></td>
              <td class="num">{{ r.n_vars }}</td>
              <td class="num">{{ r.soporte.toFixed(3) }}</td>
              <td class="num">{{ pct(r.confianza) }}</td>
              <td class="num lift-val">{{ r.lift.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div v-if="rulesTotal > rulesPageSize" class="pagination">
          <button class="btn btn-secondary pg-btn" :disabled="rulesPage <= 1" @click="loadRules(rulesPage - 1)">‹</button>
          <span>{{ rulesPage }} / {{ totalPages }}</span>
          <button class="btn btn-secondary pg-btn" :disabled="rulesPage >= totalPages" @click="loadRules(rulesPage + 1)">›</button>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h } from 'vue'
import { useRoute } from 'vue-router'
import { marked } from 'marked'
import { useJobStore } from '../stores/job.js'
import { getReport, getRules } from '../api/pipeline.js'

const route    = useRoute()
const jobStore = useJobStore()
const jobId    = route.params.jobId

const loading    = ref(true)
const fetchError = ref(null)
const rulesLoading = ref(false)

const reportMd  = computed(() => jobStore.reportMd)
const sensorId  = computed(() => jobStore.sensorId)
const metrica   = computed(() => jobStore.metrica)
const rules     = computed(() => jobStore.rules)
const rulesTotal     = computed(() => jobStore.rulesTotal)
const rulesPage      = computed(() => jobStore.rulesPage)
const rulesPageSize  = computed(() => jobStore.rulesPageSize)
const totalPages     = computed(() => Math.ceil(rulesTotal.value / rulesPageSize.value) || 1)

const parsedHtml = computed(() =>
  reportMd.value ? marked.parse(reportMd.value) : ''
)

// Sorting
const sortCol = ref('lift')
const sortDir = ref(-1)   // -1 = desc, 1 = asc

function toggleSort(col) {
  if (sortCol.value === col) sortDir.value *= -1
  else { sortCol.value = col; sortDir.value = -1 }
}

const sortedRules = computed(() => {
  const col = sortCol.value
  const dir = sortDir.value
  return [...rules.value].sort((a, b) => {
    const va = a[col], vb = b[col]
    if (typeof va === 'string') return dir * va.localeCompare(vb)
    return dir * (va - vb)
  })
})

// Helpers
function pct(v) { return (v * 100).toFixed(0) + ' %' }

function consClass(c) {
  return {
    'c-muy-alta':  c === 'v_MuyAlta'  || c === 'v_OutlierAlto',
    'c-alta':      c === 'v_Alta',
    'c-media':     c === 'v_Media',
    'c-baja':      c === 'v_Baja',
    'c-muy-baja':  c === 'v_MuyBaja'  || c === 'v_OutlierBajo',
  }
}

// Sort icon component
const SortIcon = (props) => {
  if (sortCol.value !== props.col) return null
  return h('span', { class: 'sort-arrow' }, sortDir.value === -1 ? '↓' : '↑')
}

// Download
function downloadReport() {
  if (!reportMd.value) return
  const blob = new Blob([reportMd.value], { type: 'text/markdown;charset=utf-8' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `informe_${sensorId.value ?? jobId}.md`
  a.click()
  URL.revokeObjectURL(url)
}

// Data loading
async function loadRules(page = 1) {
  rulesLoading.value = true
  try {
    const { data } = await getRules(jobId, page, rulesPageSize.value)
    jobStore.applyRules(data)
  } finally {
    rulesLoading.value = false
  }
}

onMounted(async () => {
  if (!jobStore.jobId) jobStore.setJob(jobId)
  try {
    const [reportRes] = await Promise.all([
      getReport(jobId),
      loadRules(1),
    ])
    jobStore.applyReport(reportRes.data)
  } catch (e) {
    fetchError.value = e.response?.data?.detail ?? 'No se pudo cargar el informe.'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.report-page { display: flex; flex-direction: column; gap: 1rem; }

/* Toolbar */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: .8rem;
  background: #fff;
  border-radius: 10px;
  padding: .8rem 1.2rem;
  box-shadow: 0 1px 6px rgba(0,0,0,.07);
}
.toolbar-center { display: flex; gap: .5rem; flex-wrap: wrap; }
.chip {
  background: #f1f5f9;
  border-radius: 9999px;
  padding: .25rem .75rem;
  font-size: .82rem;
  color: #374151;
}

/* Loading */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 4rem;
  color: #6b7280;
}
.spinner {
  display: inline-block;
  width: 28px; height: 28px;
  border: 3px solid #e5e7eb;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-box { color: #b91c1c; padding: 1.5rem; }

/* Layout */
.report-layout {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 1.2rem;
  align-items: start;
}

@media (max-width: 900px) {
  .report-layout { grid-template-columns: 1fr; }
}

/* Markdown */
.report-panel { overflow: auto; }
.markdown-body { line-height: 1.7; color: #1a1a2e; }
.markdown-body :deep(h1) { font-size: 1.5rem; margin: 1.4rem 0 .6rem; border-bottom: 2px solid #e5e7eb; padding-bottom: .3rem; }
.markdown-body :deep(h2) { font-size: 1.2rem; margin: 1.2rem 0 .5rem; color: #1d4ed8; }
.markdown-body :deep(h3) { font-size: 1rem; margin: 1rem 0 .4rem; color: #374151; }
.markdown-body :deep(p)  { margin-bottom: .8rem; }
.markdown-body :deep(table) { border-collapse: collapse; width: 100%; font-size: .88rem; margin: 1rem 0; }
.markdown-body :deep(th), .markdown-body :deep(td) { border: 1px solid #e5e7eb; padding: .45rem .7rem; }
.markdown-body :deep(th) { background: #f8fafc; font-weight: 700; }
.markdown-body :deep(hr) { border: none; border-top: 1.5px solid #e5e7eb; margin: 1.5rem 0; }
.markdown-body :deep(em) { color: #6b7280; }
.markdown-body :deep(strong) { color: #111827; }
.markdown-body :deep(img) { display: none; } /* hide chart image refs */

/* Rules */
.rules-panel { position: sticky; top: 1rem; max-height: calc(100vh - 120px); overflow-y: auto; }
.rules-title { font-size: 1.05rem; font-weight: 700; margin-bottom: .2rem; }
.rules-meta  { font-size: .78rem; color: #9ca3af; margin-bottom: .8rem; }
.rules-loading { display: flex; justify-content: center; padding: 2rem; }
.empty { color: #9ca3af; font-style: italic; font-size: .9rem; }

.rules-table {
  width: 100%;
  border-collapse: collapse;
  font-size: .78rem;
}
.rules-table th {
  background: #f8fafc;
  padding: .4rem .5rem;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
  border-bottom: 2px solid #e5e7eb;
  user-select: none;
}
.rules-table th:hover { background: #e2e8f0; }
.rules-table td {
  padding: .35rem .5rem;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: top;
}
.rules-table tr:hover td { background: #f8fafc; }

.ant-cell { font-family: monospace; font-size: .72rem; word-break: break-all; max-width: 120px; }
.num { text-align: right; white-space: nowrap; }
.lift-val { font-weight: 700; color: #1d4ed8; }
.sort-arrow { margin-left: .2rem; }

/* Consecuente badges */
.badge-cons {
  display: inline-block;
  padding: .15rem .45rem;
  border-radius: 4px;
  font-size: .7rem;
  font-weight: 600;
  white-space: nowrap;
}
.c-muy-alta  { background: #fef2f2; color: #991b1b; }
.c-alta      { background: #fff7ed; color: #9a3412; }
.c-media     { background: #fefce8; color: #713f12; }
.c-baja      { background: #eff6ff; color: #1e40af; }
.c-muy-baja  { background: #f0fdf4; color: #065f46; }

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: .8rem;
  padding-top: .8rem;
  font-size: .85rem;
}
.pg-btn { padding: .3rem .7rem; }
</style>
