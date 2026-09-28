---
type: specification
feature: Task due dates
slug: task-due-dates
date: 2026-01-15
branch: master
status: approved
---

# Task due dates

## Problem
Tasks have no deadline, so users cannot see which open tasks are late.

## Requirements
- A task may carry an optional due date (ISO `YYYY-MM-DD`).
- The store can list overdue tasks: open tasks whose due date is before a given day.
- The serialized task includes `due_date` (`null` when unset).
- The web list marks overdue tasks.

## Acceptance Criteria
- **AC-1** `TaskStore.add` accepts an optional `due_date`; an invalid date raises `ValueError`.
- **AC-2** `TaskStore.overdue(today)` returns open tasks with `due_date < today`, ordered by due date; done tasks are never overdue.
- **AC-3** `serialize()` includes `due_date` as an ISO string or `null`.
- **AC-4** `renderTaskList` adds the class `task--overdue` to overdue items when given `{ today }`.

## Non-Goals
- Persistence: the store stays in memory.
- Reminders or notifications.

## Boundaries
- Always: keep the store dependency-free (standard library only).
- Never: change the existing `status` values.
