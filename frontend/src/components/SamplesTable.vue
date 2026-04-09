<script setup lang="ts">
import { computed } from 'vue'

import type { SampleResult } from '../types'

const props = defineProps<{
  items: SampleResult[]
}>()

const rows = computed(() => props.items.slice(0, 50))
</script>

<template>
  <el-table :data="rows" stripe height="420" class="samples-table">
    <el-table-column prop="sample_id" label="样本 ID" min-width="110" />
    <el-table-column prop="group" label="分组" min-width="110" />
    <el-table-column label="题干摘要" min-width="260">
      <template #default="{ row }">
        <div class="cell-text">{{ row.question_summary }}</div>
      </template>
    </el-table-column>
    <el-table-column label="模型原始输出" min-width="260">
      <template #default="{ row }">
        <div class="cell-text">{{ row.raw_output || '无' }}</div>
      </template>
    </el-table-column>
    <el-table-column prop="parsed_answer" label="解析答案" min-width="100" />
    <el-table-column prop="reference_answer" label="标准答案" min-width="100" />
    <el-table-column label="是否正确" min-width="100">
      <template #default="{ row }">
        <el-tag size="small" :type="row.is_correct ? 'success' : row.status === 'error' ? 'danger' : 'warning'">
          {{ row.is_correct ? '正确' : row.status === 'error' ? '失败' : '错误' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="错误原因" min-width="220">
      <template #default="{ row }">
        <div class="cell-text">{{ row.error_reason || '-' }}</div>
      </template>
    </el-table-column>
  </el-table>
</template>

<style scoped>
.samples-table :deep(.el-table__cell) {
  vertical-align: top;
}

.cell-text {
  color: #20383d;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
