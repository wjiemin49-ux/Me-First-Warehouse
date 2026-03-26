export type TaskStatus = "todo" | "in_progress" | "done";

export type AuthUser = {
  id: string;
  email: string;
};

export type Project = {
  id: string;
  name: string;
};

export type Task = {
  id: string;
  projectId: string;
  title: string;
  description: string;
  status: TaskStatus;
  dueDate: string | null;
};

export type TaskFiltersState = {
  status: "all" | TaskStatus;
  keyword: string;
  overdue: boolean;
};
