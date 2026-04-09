<script setup lang="ts">
defineProps<{
  logs: string[]
}>()
</script>

<template>
  <div class="log-panel">
    <div v-if="logs.length === 0" class="log-empty">日志会在任务启动后实时显示。</div>
    <pre v-else class="log-content">{{ logs.join('\n') }}</pre>
  </div>
</template>

<style scoped>
.log-panel {
  min-height: 260px;
  max-height: 480px;
  overflow: auto;
  border-radius: 20px;
  padding: 24px;
  background: #0f172a;
  color: #e2e8f0;
  border: 1px solid #1e293b;
  box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.06);
  position: relative;
}

.log-panel::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 150px;
  height: 150px;
  background: radial-gradient(circle at top right, rgba(99, 102, 241, 0.1), transparent 70%);
  pointer-events: none;
}

.log-empty {
  color: #64748b;
  font-size: 14px;
  text-align: center;
  padding-top: 100px;
}

.log-content {
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', 'IBM Plex Mono', monospace;
  font-size: 13px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
