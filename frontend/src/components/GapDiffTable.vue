<script setup lang="ts">
import type { GapItem } from '@/types'
defineProps<{ items: GapItem[] }>()
</script>

<template>
  <div class="gap-table-wrapper">
    <table class="gap-table">
      <thead>
        <tr>
          <th>Requirement</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, i) in items" :key="i">
          <td>
            <span class="requirement-text">{{ item.requirement }}</span>
            <span v-if="item.evidence" class="evidence-text">{{ item.evidence }}</span>
          </td>
          <td>
            <span :class="['gap-badge', `gap-badge--${item.match_level}`]">
              {{ item.match_level === 'strong' ? 'Strong' : item.match_level === 'partial' ? 'Partial' : 'Gap' }}
            </span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.gap-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: 6px;
}

.gap-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface-1);
}

.gap-table thead tr {
  background: var(--color-surface-2);
}

.gap-table th {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-align: left;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-border);
}

.gap-table td {
  padding: 8px 16px;
  vertical-align: top;
  border-bottom: 1px solid var(--color-border);
}

.gap-table tbody tr:last-child td {
  border-bottom: none;
}

.requirement-text {
  display: block;
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.5;
}

.evidence-text {
  display: block;
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.gap-badge {
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
  display: inline-block;
  white-space: nowrap;
}

.gap-badge--strong {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.gap-badge--partial {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.gap-badge--missing {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}
</style>
