import { apiRequest } from "../../api/client";
import type { Task, TaskStatus } from "../../types";

type TaskListData = {
  tasks?: Task[];
};

type TaskData = {
  task?: Task;
};

type ListTaskFilters = {
  projectId: string;
  status: "all" | TaskStatus;
  keyword: string;
  overdue: boolean;
};

type CreateTaskPayload = {
  projectId: string;
  title: string;
  description: string;
  dueDate: string | null;
};

type UpdateTaskPayload = Partial<{
  title: string;
  description: string;
  dueDate: string | null;
  status: TaskStatus;
}>;

export async function listTasks(filters: ListTaskFilters) {
  const search = new URLSearchParams();
  search.set("projectId", filters.projectId);
  if (filters.status !== "all") {
    search.set("status", filters.status);
  }
  if (filters.keyword.trim()) {
    search.set("q", filters.keyword.trim());
  }
  if (filters.overdue) {
    search.set("overdue", "true");
  }

  const data = await apiRequest<TaskListData | Task[]>(`/api/tasks?${search.toString()}`);
  if (Array.isArray(data)) {
    return data;
  }
  return data.tasks ?? [];
}

export async function createTask(payload: CreateTaskPayload) {
  const data = await apiRequest<TaskData | Task>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(payload)
  });
  if (data && typeof data === "object" && "id" in data) {
    return data;
  }
  if (!data.task) {
    throw new Error("Task creation response missing task data.");
  }
  return data.task;
}

export async function updateTask(taskId: string, payload: UpdateTaskPayload) {
  const data = await apiRequest<TaskData | Task>(`/api/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
  if (data && typeof data === "object" && "id" in data) {
    return data;
  }
  if (!data.task) {
    throw new Error("Task update response missing task data.");
  }
  return data.task;
}

export async function deleteTask(taskId: string) {
  await apiRequest<null>(`/api/tasks/${taskId}`, {
    method: "DELETE"
  });
}
