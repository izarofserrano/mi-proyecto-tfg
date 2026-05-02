import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

export function runPipeline(formData) {
  return api.post('/api/v1/pipeline/run', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function getStatus(jobId) {
  return api.get(`/api/v1/pipeline/${jobId}/status`)
}

export function getReport(jobId) {
  return api.get(`/api/v1/pipeline/${jobId}/report`)
}

export function getRules(jobId, page = 1, pageSize = 50) {
  return api.get(`/api/v1/pipeline/${jobId}/rules`, {
    params: { page, page_size: pageSize },
  })
}
