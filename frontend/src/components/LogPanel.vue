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
  position: relative;
  min-height: 260px;
  max-height: 480px;
  overflow: auto;
  border-radius: 24px;
  padding: 24px;
  background:
    radial-gradient(circle at top right, rgba(34, 211, 238, 0.12), transparent 30%),
    radial-gradient(circle at bottom left, rgba(249, 115, 22, 0.08), transparent 26%),
    linear-gradient(180deg, rgba(9, 18, 34, 0.9), rgba(14, 24, 42, 0.95));
  color: #dfebf8;
  border: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    0 18px 40px rgba(15, 23, 42, 0.18);
}

.log-panel::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle at top right, rgba(255, 255, 255, 0.08), transparent 70%);
  pointer-events: none;
}

.log-empty {
  color: #7f95af;
  font-size: 14px;
  text-align: center;
  padding-top: 100px;
}

.log-content {
  margin: 0;
  font-family: 'JetBrains Mono', 'Fira Code', 'IBM Plex Mono', monospace;
  font-size: 13px;
  line-height: 1.85;
  color: #d8e6f7;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
