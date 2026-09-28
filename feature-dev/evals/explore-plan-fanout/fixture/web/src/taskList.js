// Renders the task list returned by the backend's serialize().
export function renderTaskList(tasks, { status } = {}) {
  const visible = status ? tasks.filter((t) => t.status === status) : tasks;
  if (visible.length === 0) {
    return '<p class="empty">No tasks</p>';
  }
  const items = visible
    .map((t) => `<li data-id="${t.id}" class="task task--${t.status}">${escapeHtml(t.title)}</li>`)
    .join('');
  return `<ul class="task-list">${items}</ul>`;
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}
