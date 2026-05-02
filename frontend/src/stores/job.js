import { defineStore } from 'pinia'

export const useJobStore = defineStore('job', {
  state: () => ({
    jobId: null,
    status: null,
    progress: 0,
    step: null,
    sensorId: null,
    metrica: null,
    reportMd: null,
    errorMsg: null,
    rules: [],
    rulesTotal: 0,
    rulesPage: 1,
    rulesPageSize: 50,
  }),

  actions: {
    setJob(jobId) {
      this.$reset()
      this.jobId = jobId
    },

    applyStatus(data) {
      this.status   = data.status
      this.progress = data.progress
      this.step     = data.step
      this.sensorId = data.sensor_id
      this.metrica  = data.metrica
      this.errorMsg = data.error_msg ?? null
    },

    applyReport(data) {
      this.reportMd = data.report_md
      this.sensorId = data.sensor_id ?? this.sensorId
      this.metrica  = data.metrica  ?? this.metrica
    },

    applyRules(data) {
      this.rules        = data.rules
      this.rulesTotal   = data.total
      this.rulesPage    = data.page
      this.rulesPageSize = data.page_size
    },
  },
})
