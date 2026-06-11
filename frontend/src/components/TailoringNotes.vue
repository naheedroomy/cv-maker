<script setup lang="ts">
import type { TailoringNote } from '@/types'
defineProps<{ notes: TailoringNote[] }>()

const actionLabels: Record<string, string> = {
  modified: 'Modified',
  added: 'Added',
  removed: 'Removed',
  reordered: 'Reordered',
  unchanged: 'Unchanged',
}

const actionClasses: Record<string, string> = {
  modified: 'action--modified',
  added: 'action--added',
  removed: 'action--removed',
  reordered: 'action--reordered',
  unchanged: 'action--unchanged',
}
</script>

<template>
  <div class="tailoring-notes">
    <h3 class="section-heading">AI Tailoring Notes</h3>
    <div class="table-wrapper">
      <table class="notes-table">
        <thead>
          <tr>
            <th>Section</th>
            <th>Action</th>
            <th>Change</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(note, i) in notes" :key="i">
            <td class="cell-section">{{ note.section }}</td>
            <td>
              <span :class="['action-badge', actionClasses[note.action] || 'action--modified']">
                {{ actionLabels[note.action] || note.action }}
              </span>
            </td>
            <td class="cell-change">{{ note.change }}</td>
            <td class="cell-reason">{{ note.reason }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.tailoring-notes {
  margin-top: 48px;
}

.section-heading {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 16px;
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: 6px;
}

.notes-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface-1);
}

.notes-table thead tr {
  background: var(--color-warning-bg);
}

.notes-table th {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-warning-text);
  text-align: left;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.notes-table td {
  padding: 10px 16px;
  vertical-align: top;
  border-bottom: 1px solid var(--color-surface-2);
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.notes-table tbody tr:last-child td {
  border-bottom: none;
}

.cell-section {
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.cell-change {
  min-width: 200px;
}

.cell-reason {
  color: var(--color-text-tertiary);
  min-width: 150px;
}

.action-badge {
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  display: inline-block;
  white-space: nowrap;
}

.action--modified {
  background: var(--color-surface-3);
  color: var(--color-accent-primary);
}

.action--added {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.action--removed {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.action--reordered {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.action--unchanged {
  background: var(--color-surface-2);
  color: var(--color-text-tertiary);
}
</style>
