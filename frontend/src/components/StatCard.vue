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
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  padding: 20px;
  min-height: 112px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.62), rgba(255, 255, 255, 0.38)),
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.42), transparent 34%);
  border: 1px solid rgba(255, 255, 255, 0.44);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.7),
    0 16px 34px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(16px) saturate(145%);
  -webkit-backdrop-filter: blur(16px) saturate(145%);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.stat-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto;
  height: 4px;
  background: linear-gradient(90deg, rgba(14, 165, 233, 0.9), rgba(20, 184, 166, 0.9), rgba(249, 115, 22, 0.85));
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.78),
    0 24px 40px rgba(15, 23, 42, 0.12);
}

.stat-card[data-tone='success'] {
  background:
    linear-gradient(180deg, rgba(240, 253, 250, 0.7), rgba(255, 255, 255, 0.42)),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.18), transparent 34%);
}

.stat-card[data-tone='success'] .stat-value {
  color: #0f8a63;
}

.stat-card[data-tone='warning'] {
  background:
    linear-gradient(180deg, rgba(255, 247, 237, 0.72), rgba(255, 255, 255, 0.42)),
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.18), transparent 34%);
}

.stat-card[data-tone='warning'] .stat-value {
  color: #d66a06;
}

.stat-label {
  font-family: 'Geist', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  color: #7b8ca1;
  margin-bottom: 16px;
}

.stat-value {
  font-family: 'Geist', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 30px;
  line-height: 1;
  font-weight: 760;
  color: #11263d;
  letter-spacing: -0.045em;
  font-variant-numeric: tabular-nums lining-nums;
}
</style>
