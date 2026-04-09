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
  border-radius: 20px;
  color: #94a3b8;
  background: rgba(248, 250, 252, 0.5);
  border: 1px dashed #e2e8f0;
  font-size: 14px;
}

.history-item {
  text-align: left;
  width: 100%;
  padding: 20px;
  border-radius: 20px;
  border: 1px solid rgba(226, 232, 240, 0.8);
  background: white;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.history-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  border-color: #6366f1;
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
  color: #1e293b;
  margin-bottom: 12px;
}

.history-item__meta {
  justify-content: flex-start;
  color: #64748b;
  font-size: 13px;
  margin-bottom: 12px;
}

.history-item__meta .el-icon {
  color: #6366f1;
  font-size: 16px;
}

.history-item__foot {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
}

.history-item__foot span:last-child {
  color: #6366f1;
  font-weight: 700;
}
</style>
