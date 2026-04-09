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
  max-height: 420px;
  overflow: auto;
  border-radius: 20px;
  padding: 16px;
  background:
    linear-gradient(135deg, rgba(12, 23, 26, 0.96), rgba(25, 39, 44, 0.98)),
    radial-gradient(circle at top right, rgba(195, 162, 94, 0.08), transparent 42%);
  color: #dbebe7;
  border: 1px solid rgba(16, 43, 45, 0.12);
}

.log-empty {
  color: rgba(219, 235, 231, 0.68);
  font-size: 14px;
}

.log-content {
  margin: 0;
  font-family: 'IBM Plex Mono', 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
