import axios from 'axios'

import type { DatasetInfo, EvaluationJob, EvaluationPayload } from '../types'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
  timeout: 30000
})

export async function fetchDatasets(): Promise<DatasetInfo[]> {
  const response = await api.get<{ items: DatasetInfo[] }>('/datasets')
  return response.data.items
}

export async function startEvaluation(payload: EvaluationPayload): Promise<EvaluationJob> {
  const response = await api.post<EvaluationJob>('/evaluations/run', payload)
  return response.data
}

export async function fetchEvaluation(jobId: string): Promise<EvaluationJob> {
  const response = await api.get<EvaluationJob>(`/evaluations/${jobId}`)
  return response.data
}

export async function fetchHistory(): Promise<EvaluationJob[]> {
  const response = await api.get<{ items: EvaluationJob[] }>('/evaluations')
  return response.data.items
}
