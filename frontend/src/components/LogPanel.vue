<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  logs: string[]
}>()

interface LogSegment {
  text: string
  className: string
}

const TOKEN_PATTERN = /\[[^\]]+\]|解析答案=[^，]+|判定=正确|判定=错误/g
const TIMESTAMP_PATTERN = /^\[(\d{4}-\d{2}-\d{2}T[^\]]+)\]\s*/

const renderedLines = computed(() =>
  props.logs.map((line, lineIndex) => ({
    key: `${lineIndex}-${line}`,
    segments: splitLine(line)
  }))
)

function splitLine(line: string): LogSegment[] {
  const segments: LogSegment[] = []
  let content = line

  const timestampMatch = content.match(TIMESTAMP_PATTERN)
  if (timestampMatch) {
    segments.push({ text: `[${timestampMatch[1]}]`, className: 'is-timestamp' })
    content = content.slice(timestampMatch[0].length)
    if (timestampMatch[0].endsWith(' ')) {
      segments.push({ text: ' ', className: 'is-plain' })
    }
  }

  let lastIndex = 0
  for (const match of content.matchAll(TOKEN_PATTERN)) {
    const matchIndex = match.index ?? 0
    if (matchIndex > lastIndex) {
      segments.push({
        text: content.slice(lastIndex, matchIndex),
        className: 'is-plain'
      })
    }

    const token = match[0]
    segments.push({
      text: token,
      className: resolveTokenClass(token)
    })
    lastIndex = matchIndex + token.length
  }

  if (lastIndex < content.length) {
    segments.push({
      text: content.slice(lastIndex),
      className: 'is-plain'
    })
  }

  if (segments.length === 0) {
    segments.push({ text: line, className: 'is-plain' })
  }

  return segments
}

function resolveTokenClass(token: string): string {
  if (token.startsWith('[') && token.endsWith(']')) {
    return 'is-tag'
  }
  if (token.startsWith('解析答案=')) {
    return 'is-answer'
  }
  if (token === '判定=正确') {
    return 'is-success'
  }
  if (token === '判定=错误') {
    return 'is-error'
  }
  return 'is-plain'
}
</script>

<template>
  <div class="log-panel">
    <div v-if="logs.length === 0" class="log-empty">日志会在任务启动后实时显示。</div>
    <div v-else class="log-content">
      <div v-for="line in renderedLines" :key="line.key" class="log-line">
        <template v-for="(segment, index) in line.segments" :key="`${line.key}-${index}`">
          <span class="log-token" :class="segment.className">{{ segment.text }}</span>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.log-panel {
  position: relative;
  min-height: 260px;
  max-height: 480px;
  overflow: auto;
  border-radius: 22px;
  padding: 18px 20px;
  background:
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 28%),
    radial-gradient(circle at bottom left, rgba(45, 212, 191, 0.06), transparent 24%),
    linear-gradient(180deg, rgba(34, 45, 62, 0.98), rgba(24, 34, 49, 0.98));
  color: #dbe7f5;
  border: 1px solid rgba(148, 163, 184, 0.16);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.05),
    inset 0 -1px 0 rgba(255, 255, 255, 0.03),
    0 16px 34px rgba(15, 23, 42, 0.16);
  backdrop-filter: blur(12px) saturate(118%);
  -webkit-backdrop-filter: blur(12px) saturate(118%);
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.34) transparent;
}

.log-panel::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 180px;
  height: 180px;
  background: radial-gradient(circle at top right, rgba(255, 255, 255, 0.06), transparent 72%);
  pointer-events: none;
}

.log-panel::-webkit-scrollbar {
  width: 8px;
}

.log-panel::-webkit-scrollbar-track {
  background: transparent;
}

.log-panel::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(148, 163, 184, 0.34), rgba(100, 116, 139, 0.26));
  border: 2px solid transparent;
  background-clip: padding-box;
}

.log-panel::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(148, 163, 184, 0.48), rgba(100, 116, 139, 0.38));
  background-clip: padding-box;
}

.log-empty {
  color: #90a0b6;
  font-size: 14px;
  text-align: center;
  padding-top: 100px;
  font-weight: 460;
}

.log-content {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 6px;
  font-family: 'JetBrains Mono', 'Geist Mono', 'SF Mono', 'Fira Code', 'IBM Plex Mono', monospace;
  font-size: 12.5px;
  line-height: 1.9;
  font-weight: 450;
  color: #d5e3f2;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-line {
  padding: 2px 0;
}

.log-token {
  white-space: pre-wrap;
}

.is-plain {
  color: #d5e3f2;
}

.is-timestamp {
  color: #7f91a8;
}

.is-tag {
  color: #c2d2e7;
  font-weight: 560;
}

.is-answer {
  color: #f3f7fc;
  font-weight: 560;
}

.is-success {
  color: #67d7ad;
  font-weight: 600;
}

.is-error {
  color: #f5ae8a;
  font-weight: 600;
}
</style>
