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
  gap: 12px;
}

.history-empty {
  padding: 24px;
  border-radius: 16px;
  color: #6e8183;
  background: rgba(248, 248, 245, 0.8);
  border: 1px dashed rgba(20, 48, 52, 0.16);
}

.history-item {
  text-align: left;
  width: 100%;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(20, 48, 52, 0.12);
  background: rgba(255, 255, 255, 0.9);
  cursor: pointer;
  transition: transform 140ms ease, box-shadow 140ms ease;
}

.history-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 26px rgba(17, 32, 36, 0.07);
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
  font-weight: 600;
  color: #163135;
  margin-bottom: 10px;
}

.history-item__meta {
  justify-content: flex-start;
  color: #627678;
  margin-bottom: 10px;
}

.history-item__foot {
  color: #7b8d8f;
  font-size: 12px;
}
</style>
