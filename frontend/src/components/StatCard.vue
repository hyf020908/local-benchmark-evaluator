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
  border-radius: 18px;
  padding: 18px 18px 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(18, 49, 52, 0.12);
  box-shadow: 0 14px 32px rgba(20, 36, 41, 0.06);
}

.stat-card[data-tone='success'] {
  background: linear-gradient(180deg, rgba(231, 246, 237, 0.98), rgba(247, 252, 249, 0.98));
}

.stat-card[data-tone='warning'] {
  background: linear-gradient(180deg, rgba(255, 244, 228, 0.98), rgba(255, 252, 246, 0.98));
}

.stat-label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #687d7f;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 30px;
  line-height: 1;
  font-weight: 700;
  color: #143034;
}
</style>
