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
  color: #111827;
  margin-bottom: 16px;
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.notes-table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
}

.notes-table thead tr {
  background: #fffbeb;
}

.notes-table th {
  font-size: 12px;
  font-weight: 600;
  color: #92400e;
  text-align: left;
  padding: 8px 16px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.notes-table td {
  padding: 10px 16px;
  vertical-align: top;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
  color: #374151;
  line-height: 1.5;
}

.notes-table tbody tr:last-child td {
  border-bottom: none;
}

.cell-section {
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
}

.cell-change {
  min-width: 200px;
}

.cell-reason {
  color: #6b7280;
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
  background: #dbeafe;
  color: #1e40af;
}

.action--added {
  background: #dcfce7;
  color: #14532d;
}

.action--removed {
  background: #fee2e2;
  color: #991b1b;
}

.action--reordered {
  background: #fef3c7;
  color: #92400e;
}

.action--unchanged {
  background: #f3f4f6;
  color: #6b7280;
}
</style>
