const API = "/api/todos";

const todoForm = document.getElementById("todoForm");
const titleInput = document.getElementById("titleInput");
const descriptionInput = document.getElementById("descriptionInput");
const priorityInput = document.getElementById("priorityInput");
const todoList = document.getElementById("todoList");
const emptyState = document.getElementById("emptyState");
const filtersEl = document.getElementById("filters");
const searchInput = document.getElementById("searchInput");
const clearCompletedBtn = document.getElementById("clearCompletedBtn");
const toast = document.getElementById("toast");

const statTotal = document.getElementById("statTotal");
const statActive = document.getElementById("statActive");
const statCompleted = document.getElementById("statCompleted");

const editModalOverlay = document.getElementById("editModalOverlay");
const editForm = document.getElementById("editForm");
const editTitle = document.getElementById("editTitle");
const editDescription = document.getElementById("editDescription");
const editPriority = document.getElementById("editPriority");
const cancelEditBtn = document.getElementById("cancelEditBtn");

let currentFilter = "all";
let currentSearch = "";
let editingId = null;
let searchDebounce = null;

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function formatDate(iso) {
  const d = new Date(iso + "Z");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) +
    " " + d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

async function fetchTodos() {
  const params = new URLSearchParams({ status: currentFilter, search: currentSearch });
  const res = await fetch(`${API}?${params.toString()}`);
  const data = await res.json();
  renderTodos(data.todos);
  renderStats(data.stats);
}

function renderStats(stats) {
  statTotal.textContent = stats.total;
  statActive.textContent = stats.active;
  statCompleted.textContent = stats.completed;
}

function renderTodos(todos) {
  todoList.innerHTML = "";
  emptyState.hidden = todos.length !== 0;

  todos.forEach((todo) => {
    const li = document.createElement("li");
    li.className = `todo-item priority-${todo.priority}${todo.completed ? " completed" : ""}`;
    li.dataset.id = todo.id;

    li.innerHTML = `
      <button class="checkbox-btn ${todo.completed ? "checked" : ""}" title="${todo.completed ? "Mark as not done" : "Mark as done"}">
        ${todo.completed ? "✓" : ""}
      </button>
      <div class="todo-body">
        <p class="todo-title">${escapeHtml(todo.title)}</p>
        ${todo.description ? `<p class="todo-desc">${escapeHtml(todo.description)}</p>` : ""}
        <div class="todo-meta">
          <span class="badge priority-${todo.priority}">${todo.priority}</span>
          <span class="todo-date">Created ${formatDate(todo.created_at)}</span>
        </div>
      </div>
      <div class="todo-actions">
        <button class="icon-btn edit-btn" title="Edit">✏️</button>
        <button class="icon-btn delete delete-btn" title="Delete">🗑️</button>
      </div>
    `;

    li.querySelector(".checkbox-btn").addEventListener("click", () => toggleTodo(todo.id));
    li.querySelector(".edit-btn").addEventListener("click", () => openEditModal(todo));
    li.querySelector(".delete-btn").addEventListener("click", () => deleteTodo(todo.id, li));

    todoList.appendChild(li);
  });
}

async function addTodo(e) {
  e.preventDefault();
  const title = titleInput.value.trim();
  if (!title) return;

  const payload = {
    title,
    description: descriptionInput.value.trim(),
    priority: priorityInput.value,
  };

  const res = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    titleInput.value = "";
    descriptionInput.value = "";
    priorityInput.value = "medium";
    showToast("Task added");
    fetchTodos();
  } else {
    const err = await res.json();
    showToast(err.error || "Failed to add task");
  }
  titleInput.focus();
}

async function toggleTodo(id) {
  await fetch(`${API}/${id}/toggle`, { method: "PATCH" });
  fetchTodos();
}

async function deleteTodo(id, li) {
  li.style.transition = "opacity 0.2s, transform 0.2s";
  li.style.opacity = "0";
  li.style.transform = "translateX(20px)";
  setTimeout(async () => {
    await fetch(`${API}/${id}`, { method: "DELETE" });
    showToast("Task deleted");
    fetchTodos();
  }, 180);
}

function openEditModal(todo) {
  editingId = todo.id;
  editTitle.value = todo.title;
  editDescription.value = todo.description || "";
  editPriority.value = todo.priority;
  editModalOverlay.classList.add("open");
  setTimeout(() => editTitle.focus(), 50);
}

function closeEditModal() {
  editModalOverlay.classList.remove("open");
  editingId = null;
}

async function saveEdit(e) {
  e.preventDefault();
  if (!editingId) return;

  const payload = {
    title: editTitle.value.trim(),
    description: editDescription.value.trim(),
    priority: editPriority.value,
  };

  const res = await fetch(`${API}/${editingId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (res.ok) {
    showToast("Task updated");
    closeEditModal();
    fetchTodos();
  } else {
    const err = await res.json();
    showToast(err.error || "Failed to update task");
  }
}

filtersEl.addEventListener("click", (e) => {
  const btn = e.target.closest(".filter-btn");
  if (!btn) return;
  document.querySelectorAll(".filter-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  currentFilter = btn.dataset.filter;
  fetchTodos();
});

searchInput.addEventListener("input", () => {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    currentSearch = searchInput.value.trim();
    fetchTodos();
  }, 250);
});

clearCompletedBtn.addEventListener("click", async () => {
  await fetch(`${API}/clear-completed`, { method: "DELETE" });
  showToast("Completed tasks cleared");
  fetchTodos();
});

todoForm.addEventListener("submit", addTodo);
editForm.addEventListener("submit", saveEdit);
cancelEditBtn.addEventListener("click", closeEditModal);
editModalOverlay.addEventListener("click", (e) => {
  if (e.target === editModalOverlay) closeEditModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && editModalOverlay.classList.contains("open")) closeEditModal();
});

fetchTodos();
