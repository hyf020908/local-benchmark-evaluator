<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  tone?: 'neutral' | 'success' | 'warning'
}>()
</script>

<template>
  <div class="stat-card" :data-tone="tone || 'neutral'">
    <div class="stat-label">{{ label }}</div>
    <div class="stat-value">{{ value }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  border-radius: 20px;
  padding: 20px;
  background: white;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 100px;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.08);
  border-color: #6366f1;
}

.stat-card[data-tone='success'] {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.05) 0%, rgba(255, 255, 255, 1) 100%);
}

.stat-card[data-tone='success'] .stat-value {
  color: #16a34a;
}

.stat-card[data-tone='warning'] {
  background: linear-gradient(135deg, rgba(249, 115, 22, 0.05) 0%, rgba(255, 255, 255, 1) 100%);
}

.stat-card[data-tone='warning'] .stat-value {
  color: #ea580c;
}

.stat-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #64748b;
  margin-bottom: 12px;
}

.stat-value {
  font-size: 28px;
  line-height: 1;
  font-weight: 800;
  color: #1e293b;
  letter-spacing: -0.02em;
}
</style>
