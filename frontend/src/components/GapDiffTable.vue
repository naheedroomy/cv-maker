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
            <span :class="['gap-badge', item.present ? 'gap-badge--met' : 'gap-badge--gap']">
              {{ item.present ? 'Met' : 'Gap' }}
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
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.gap-table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
}

.gap-table thead tr {
  background: #f8f9fa;
}

.gap-table th {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  text-align: left;
  padding: 8px 16px;
  border-bottom: 1px solid #e2e8f0;
}

.gap-table td {
  padding: 8px 16px;
  vertical-align: top;
  border-bottom: 1px solid #e2e8f0;
}

.gap-table tbody tr:last-child td {
  border-bottom: none;
}

.requirement-text {
  display: block;
  font-size: 14px;
  color: #111827;
  line-height: 1.5;
}

.evidence-text {
  display: block;
  font-size: 12px;
  color: #6b7280;
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

.gap-badge--met {
  background: #dcfce7;
  color: #14532d;
}

.gap-badge--gap {
  background: #fee2e2;
  color: #991b1b;
}
</style>
