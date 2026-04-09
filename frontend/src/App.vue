<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { DocumentCopy, Promotion, RefreshRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

import { fetchDatasets, fetchEvaluation, fetchHistory, startEvaluation } from './api/client'
import HistoryList from './components/HistoryList.vue'
import LogPanel from './components/LogPanel.vue'
import SamplesTable from './components/SamplesTable.vue'
import StatCard from './components/StatCard.vue'
import type { DatasetInfo, EvaluationJob, EvaluationPayload } from './types'

const datasets = ref<DatasetInfo[]>([])
const history = ref<EvaluationJob[]>([])
const currentJob = ref<EvaluationJob | null>(null)
const loading = ref(false)
const polling = ref<number | null>(null)
const pollingInFlight = ref(false)
const pollingFailures = ref(0)
const activeTab = ref('samples')
const POLL_INTERVAL_MS = 1500
const POLL_RETRY_MS = 4000

const form = reactive<EvaluationPayload>({
  base_url: 'http://127.0.0.1:8001',
  api_key: '',
  model: 'gpt-4o-mini',
  dataset_path: '',
  dataset_type: 'auto',
  max_samples: 12,
  concurrency: 2,
  temperature: 0,
  timeout_seconds: 120,
  few_shot: 0
})

const progressPercentage = computed(() => {
  if (!currentJob.value?.progress.total) return 0
  return Math.round((currentJob.value.progress.completed / currentJob.value.progress.total) * 100)
})

const summaryItems = computed(() => {
  const metrics = currentJob.value?.metrics
  const progress = currentJob.value?.progress
  return [
    { label: '总题数', value: metrics?.total_questions ?? progress?.total ?? 0 },
    { label: '已完成', value: metrics?.completed_questions ?? progress?.completed ?? 0 },
    { label: '成功题数', value: metrics?.success_questions ?? progress?.success ?? 0, tone: 'success' as const },
    { label: '失败题数', value: metrics?.failed_questions ?? progress?.failed ?? 0, tone: 'warning' as const },
    { label: '正确数', value: metrics?.correct_questions ?? progress?.correct ?? 0 },
    { label: '准确率', value: metrics?.accuracy !== undefined ? `${(Number(metrics.accuracy) * 100).toFixed(2)}%` : '--' },
    { label: '总耗时', value: metrics?.total_elapsed_seconds !== undefined ? `${Number(metrics.total_elapsed_seconds).toFixed(2)}s` : '--' },
    { label: '平均每题', value: metrics?.avg_seconds_per_question !== undefined ? `${Number(metrics.avg_seconds_per_question).toFixed(2)}s` : '--' }
  ]
})

async function loadInitialData() {
  const [datasetItems, historyItems] = await Promise.all([fetchDatasets(), fetchHistory()])
  datasets.value = datasetItems
  history.value = historyItems
}

function stopPolling() {
  if (polling.value !== null) {
    window.clearTimeout(polling.value)
    polling.value = null
  }
  pollingInFlight.value = false
  pollingFailures.value = 0
}

async function refreshCurrentJob() {
  if (!currentJob.value) return
  const latest = await fetchEvaluation(currentJob.value.id)
  currentJob.value = latest
  if (latest.status === 'completed' || latest.status === 'failed') {
    stopPolling()
    history.value = await fetchHistory()
  }
}

function schedulePolling(delay = POLL_INTERVAL_MS) {
  if (polling.value !== null) {
    window.clearTimeout(polling.value)
  }
  polling.value = window.setTimeout(runPollingCycle, delay)
}

async function runPollingCycle() {
  if (!currentJob.value || pollingInFlight.value) {
    schedulePolling()
    return
  }

  pollingInFlight.value = true
  try {
    await refreshCurrentJob()
    pollingFailures.value = 0
    if (currentJob.value?.status === 'running' || currentJob.value?.status === 'queued') {
      schedulePolling()
    }
  } catch (error: any) {
    pollingFailures.value += 1
    if (pollingFailures.value === 1 || pollingFailures.value % 5 === 0) {
      const detail = error?.response?.data?.detail || error?.message || '未知错误'
      ElMessage.warning(`轮询评测状态失败：${detail}`)
    }
    schedulePolling(POLL_RETRY_MS)
  } finally {
    pollingInFlight.value = false
  }
}

function startPolling() {
  stopPolling()
  schedulePolling()
}

async function submitEvaluation() {
  loading.value = true
  try {
    const job = await startEvaluation({ ...form })
    currentJob.value = job
    activeTab.value = 'logs'
    startPolling()
    ElMessage.success('评测任务已启动。')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error?.message || '启动评测失败。')
  } finally {
    loading.value = false
  }
}

async function openHistory(jobId: string) {
  currentJob.value = await fetchEvaluation(jobId)
  activeTab.value = 'samples'
  if (currentJob.value.status === 'running' || currentJob.value.status === 'queued') {
    startPolling()
  } else {
    stopPolling()
  }
}

function exportJson() {
  if (!currentJob.value) return
  const blob = new Blob([JSON.stringify(currentJob.value, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${currentJob.value.dataset_type}-${currentJob.value.model}-${currentJob.value.id}.json`
  link.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  try {
    await loadInitialData()
  } catch (error) {
    ElMessage.error('初始化失败，请确认后端已启动。')
  }
})

onBeforeUnmount(() => {
  stopPolling()
})
</script>

<template>
  <div class="shell">
    <section class="hero">
      <div>
        <div class="eyebrow">Local Multi-Benchmark LLM Evaluation</div>
        <h1>Local Benchmark Evaluator</h1>
        <p class="hero-copy">
          面向 OpenAI-compatible 模型接口的本地评测系统，统一管理 MMLU-Pro、C-Eval、CMMLU、TruthfulQA
          等评测集，支持绝对路径读取、后台任务、日志追踪与结果落盘。
        </p>
      </div>
      <div class="hero-meta">
        <span>Vue 3 + TypeScript</span>
        <span>FastAPI</span>
        <span>JSON Outputs</span>
      </div>
    </section>

    <main class="layout">
      <aside class="left-panel panel">
        <div class="panel-head">
          <div>
            <h2>评测参数</h2>
            <p>用于录入模型配置与本地评测集绝对路径，并提交评测任务。</p>
          </div>
        </div>

        <el-form label-position="top" class="form-grid">
          <el-form-item label="base_url">
            <el-input v-model="form.base_url" placeholder="http://127.0.0.1:8001" />
          </el-form-item>

          <el-form-item label="api_key">
            <el-input v-model="form.api_key" show-password placeholder="sk-..." />
          </el-form-item>

          <el-form-item label="model">
            <el-input v-model="form.model" placeholder="gpt-4o-mini" />
          </el-form-item>

          <el-form-item label="评测集类型">
            <el-select v-model="form.dataset_type" class="full-width">
              <el-option label="自动识别" value="auto" />
              <el-option
                v-for="item in datasets"
                :key="item.key"
                :label="item.label"
                :value="item.key"
              />
            </el-select>
          </el-form-item>

          <el-form-item label="数据集绝对路径">
            <el-input
              v-model="form.dataset_path"
              type="textarea"
              :rows="3"
              placeholder="/absolute/path/to/dataset"
            />
          </el-form-item>

          <div class="sub-grid">
            <el-form-item label="最大样本数">
              <el-input-number v-model="form.max_samples" :min="1" :max="5000" />
            </el-form-item>
            <el-form-item label="并发数">
              <el-input-number v-model="form.concurrency" :min="1" :max="16" />
            </el-form-item>
            <el-form-item label="温度">
              <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" />
            </el-form-item>
            <el-form-item label="超时时间(s)">
              <el-input-number v-model="form.timeout_seconds" :min="10" :max="600" />
            </el-form-item>
            <el-form-item label="Few-shot">
              <el-input-number v-model="form.few_shot" :min="0" :max="10" />
            </el-form-item>
          </div>
        </el-form>

        <div class="action-row">
          <el-button type="primary" size="large" :icon="Promotion" :loading="loading" @click="submitEvaluation">
            启动评测
          </el-button>
          <el-button size="large" :icon="RefreshRight" @click="loadInitialData">刷新</el-button>
        </div>
      </aside>

      <section class="right-panel">
        <div class="panel status-panel">
          <div class="status-header">
            <div>
              <div class="section-title">运行状态</div>
              <h2>{{ currentJob?.dataset_name || '等待任务' }}</h2>
              <p>
                {{ currentJob ? `${currentJob.model} · ${currentJob.base_url_display}` : '任务启动后显示状态、路径与结果摘要。' }}
              </p>
            </div>
            <div class="status-actions" v-if="currentJob">
              <el-tag :type="currentJob.status === 'completed' ? 'success' : currentJob.status === 'failed' ? 'danger' : 'warning'">
                {{ currentJob.status }}
              </el-tag>
              <el-button plain :icon="DocumentCopy" @click="exportJson">导出 JSON</el-button>
            </div>
          </div>

          <div class="meta-grid" v-if="currentJob">
            <div class="meta-item">
              <span>路径</span>
              <strong>{{ currentJob.dataset_path }}</strong>
            </div>
            <div class="meta-item">
              <span>掩码 API Key</span>
              <strong>{{ currentJob.api_key_masked }}</strong>
            </div>
          </div>

          <el-progress
            :percentage="progressPercentage"
            :status="currentJob?.status === 'failed' ? 'exception' : currentJob?.status === 'completed' ? 'success' : undefined"
            :stroke-width="16"
          />

          <div class="stats-grid">
            <StatCard
              v-for="item in summaryItems"
              :key="item.label"
              :label="item.label"
              :value="item.value"
              :tone="item.tone"
            />
          </div>
        </div>

        <div class="panel tabs-panel">
          <el-tabs v-model="activeTab" stretch>
            <el-tab-pane label="结果样本" name="samples">
              <SamplesTable :items="currentJob?.sample_results || []" />
            </el-tab-pane>
            <el-tab-pane label="运行日志" name="logs">
              <LogPanel :logs="currentJob?.logs || []" />
            </el-tab-pane>
            <el-tab-pane label="历史记录" name="history">
              <HistoryList :items="history" @select="openHistory" />
            </el-tab-pane>
          </el-tabs>
        </div>
      </section>
    </main>
  </div>
</template>
