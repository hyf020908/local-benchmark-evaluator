<script setup lang="ts">
import { FolderOpened } from '@element-plus/icons-vue'

import type { EvaluationJob } from '../types'

defineProps<{
  items: EvaluationJob[]
}>()

const emit = defineEmits<{
  select: [jobId: string]
}>()
</script>

<template>
  <div class="history-list">
    <div v-if="items.length === 0" class="history-empty">暂无历史记录</div>
    <button
      v-for="item in items"
      :key="item.id"
      class="history-item"
      type="button"
      @click="emit('select', item.id)"
    >
      <div class="history-item__head">
        <span>{{ item.dataset_name || item.dataset_type }}</span>
        <el-tag size="small" :type="item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'info'">
          {{ item.status }}
        </el-tag>
      </div>
      <div class="history-item__meta">
        <el-icon><FolderOpened /></el-icon>
        <span>{{ item.model }}</span>
      </div>
      <div class="history-item__foot">
        <span>{{ item.created_at?.replace('T', ' ').slice(0, 19) }}</span>
        <span v-if="item.metrics?.accuracy !== undefined">Acc {{ Number(item.metrics.accuracy).toFixed(4) }}</span>
      </div>
    </button>
  </div>
</template>

<style scoped>
.history-list {
  display: grid;
  gap: 16px;
}

.history-empty {
  padding: 48px 24px;
  text-align: center;
  border-radius: 22px;
  color: #74859a;
  background: rgba(255, 255, 255, 0.34);
  border: 1px dashed rgba(150, 168, 189, 0.42);
  font-size: 14px;
}

.history-item {
  position: relative;
  overflow: hidden;
  text-align: left;
  width: 100%;
  padding: 20px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.44);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.58), rgba(255, 255, 255, 0.38)),
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.08), transparent 35%);
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.72),
    0 14px 28px rgba(15, 23, 42, 0.07);
  backdrop-filter: blur(14px) saturate(145%);
  -webkit-backdrop-filter: blur(14px) saturate(145%);
  transition:
    transform 0.22s ease,
    box-shadow 0.22s ease,
    border-color 0.22s ease;
}

.history-item::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: linear-gradient(180deg, rgba(14, 165, 233, 0.9), rgba(20, 184, 166, 0.72), rgba(249, 115, 22, 0.7));
  opacity: 0.86;
}

.history-item:hover {
  transform: translateY(-3px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 22px 40px rgba(15, 23, 42, 0.12);
  border-color: rgba(14, 165, 233, 0.3);
}

.history-item__head,
.history-item__foot,
.history-item__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.history-item__head {
  font-weight: 700;
  font-size: 16px;
  color: #17314b;
  margin-bottom: 12px;
}

.history-item__meta {
  justify-content: flex-start;
  color: #607086;
  font-size: 13px;
  margin-bottom: 12px;
}

.history-item__meta .el-icon {
  color: #0ea5e9;
  font-size: 16px;
}

.history-item__foot {
  color: #8192a8;
  font-size: 12px;
  font-weight: 600;
}

.history-item__foot span:last-child {
  color: #0f766e;
  font-weight: 800;
}
</style>
