export interface DatasetInfo {
  key: string
  label: string
  description: string
  example_path?: string | null
  supports_auto_detect: boolean
}

export interface ProgressState {
  total: number
  completed: number
  success: number
  failed: number
  correct: number
  parsable: number
}

export interface MetricState {
  total_questions: number
  completed_questions: number
  success_questions: number
  failed_questions: number
  parsable_questions: number
  correct_questions: number
  accuracy: number
  avg_seconds_per_question: number
  total_elapsed_seconds: number
}

export interface SampleResult {
  sample_id: string
  group: string
  question_summary: string
  question: string
  raw_output: string
  parsed_answer: string | null
  reference_answer: string
  is_correct: boolean
  status: string
  error_reason: string | null
  elapsed_seconds: number
  options: string[]
}

export interface EvaluationJob {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  dataset_type: string
  dataset_name: string
  dataset_path: string
  model: string
  base_url: string
  base_url_display: string
  api_key_masked: string
  created_at: string
  started_at?: string | null
  finished_at?: string | null
  output_file?: string | null
  error_message?: string | null
  progress: ProgressState
  metrics: Partial<MetricState>
  sample_results: SampleResult[]
  logs: string[]
}

export interface EvaluationPayload {
  base_url: string
  api_key: string
  model: string
  dataset_path: string
  dataset_type: string
  max_samples: number
  concurrency: number
  temperature: number
  timeout_seconds: number
  few_shot: number
}
