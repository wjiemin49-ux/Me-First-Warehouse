import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "./components/AppShell";
import { ErrorBanner } from "./components/ErrorBanner";
import { AuthPage } from "./features/auth/AuthPage";
import { useAuth } from "./features/auth/useAuth";
import { ProjectSidebar } from "./features/projects/ProjectSidebar";
import { createProject, deleteProject, listProjects, updateProject } from "./features/projects/project-api";
import { TaskBoard } from "./features/tasks/TaskBoard";
import { TaskFilters } from "./features/tasks/TaskFilters";
import { TaskForm } from "./features/tasks/TaskForm";
import { createTask, deleteTask, listTasks, updateTask } from "./features/tasks/task-api";
import type { Project, Task, TaskFiltersState, TaskStatus } from "./types";

const DEFAULT_FILTERS: TaskFiltersState = {
  status: "all",
  keyword: "",
  overdue: false
};

function isOverdue(task: Task) {
  if (!task.dueDate) {
    return false;
  }
  if (task.status === "done") {
    return false;
  }
  const due = new Date(task.dueDate);
  return due.getTime() < Date.now();
}

export default function App() {
  const { user, pending: authPending, error: authError, login, register, logout } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filters, setFilters] = useState<TaskFiltersState>(DEFAULT_FILTERS);
  const [dashboardPending, setDashboardPending] = useState(false);
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  const selectedProject = useMemo(
    () => projects.find((project) => project.id === selectedProjectId) ?? null,
    [projects, selectedProjectId]
  );

  const loadProjects = useCallback(async () => {
    setDashboardPending(true);
    setDashboardError(null);
    try {
      const loadedProjects = await listProjects();
      setProjects(loadedProjects);
      setSelectedProjectId((current) => {
        if (current && loadedProjects.some((project) => project.id === current)) {
          return current;
        }
        return loadedProjects[0]?.id ?? null;
      });
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to load projects.");
      setProjects([]);
      setSelectedProjectId(null);
    } finally {
      setDashboardPending(false);
    }
  }, []);

  const loadTasks = useCallback(async () => {
    if (!selectedProjectId) {
      setTasks([]);
      return;
    }
    setDashboardPending(true);
    setDashboardError(null);
    try {
      const loadedTasks = await listTasks({
        projectId: selectedProjectId,
        status: filters.status,
        keyword: filters.keyword,
        overdue: filters.overdue
      });
      setTasks(loadedTasks);
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to load tasks.");
      setTasks([]);
    } finally {
      setDashboardPending(false);
    }
  }, [filters.keyword, filters.overdue, filters.status, selectedProjectId]);

  useEffect(() => {
    if (!user) {
      setProjects([]);
      setSelectedProjectId(null);
      setTasks([]);
      setFilters(DEFAULT_FILTERS);
      return;
    }
    void loadProjects();
  }, [loadProjects, user]);

  useEffect(() => {
    if (!user) {
      return;
    }
    void loadTasks();
  }, [loadTasks, user]);

  const visibleTasks = useMemo(() => {
    let result = tasks;
    if (filters.status !== "all") {
      result = result.filter((task) => task.status === filters.status);
    }
    if (filters.keyword.trim()) {
      const query = filters.keyword.trim().toLowerCase();
      result = result.filter(
        (task) =>
          task.title.toLowerCase().includes(query) || (task.description ?? "").toLowerCase().includes(query)
      );
    }
    if (filters.overdue) {
      result = result.filter((task) => isOverdue(task));
    }
    return result;
  }, [filters.keyword, filters.overdue, filters.status, tasks]);

  const handleCreateProject = async (name: string) => {
    setDashboardError(null);
    try {
      const created = await createProject(name);
      setProjects((current) => [...current, created]);
      setSelectedProjectId(created.id);
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to create project.");
    }
  };

  const handleRenameProject = async (projectId: string, name: string) => {
    setDashboardError(null);
    try {
      const updated = await updateProject(projectId, name);
      setProjects((current) => current.map((project) => (project.id === projectId ? updated : project)));
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to rename project.");
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    setDashboardError(null);
    try {
      await deleteProject(projectId);
      setProjects((current) => {
        const next = current.filter((project) => project.id !== projectId);
        setSelectedProjectId((selected) => {
          if (selected !== projectId) {
            return selected;
          }
          return next[0]?.id ?? null;
        });
        return next;
      });
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to delete project.");
    }
  };

  const refreshTasks = async () => {
    await loadTasks();
  };

  const handleCreateTask = async (payload: { title: string; description: string; dueDate: string | null }) => {
    if (!selectedProjectId) {
      setDashboardError("Select a project first.");
      return;
    }
    setDashboardError(null);
    try {
      await createTask({
        ...payload,
        projectId: selectedProjectId
      });
      await refreshTasks();
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to create task.");
    }
  };

  const handleStatusChange = async (taskId: string, status: TaskStatus) => {
    setDashboardError(null);
    try {
      await updateTask(taskId, { status });
      await refreshTasks();
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to update task status.");
    }
  };

  const handleUpdateTask = async (
    taskId: string,
    payload: Partial<{ title: string; description: string; dueDate: string | null }>
  ) => {
    setDashboardError(null);
    try {
      await updateTask(taskId, payload);
      await refreshTasks();
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to update task.");
    }
  };

  const handleDeleteTask = async (taskId: string) => {
    setDashboardError(null);
    try {
      await deleteTask(taskId);
      await refreshTasks();
    } catch (err) {
      setDashboardError(err instanceof Error ? err.message : "Unable to delete task.");
    }
  };

  if (!user) {
    return <AuthPage pending={authPending} error={authError} onLogin={login} onRegister={register} />;
  }

  return (
    <AppShell userEmail={user.email} onLogout={logout}>
      <ProjectSidebar
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelect={setSelectedProjectId}
        onCreate={handleCreateProject}
        onRename={handleRenameProject}
        onDelete={handleDeleteProject}
        pending={dashboardPending}
      />
      <main className="dashboard-main">
        {dashboardError ? <ErrorBanner message={dashboardError} /> : null}
        {!selectedProject ? (
          <section className="empty-state">
            <h2>No project selected</h2>
            <p>Create a project to start planning your tasks.</p>
          </section>
        ) : (
          <>
            <section className="dashboard-top">
              <h2>{selectedProject.name}</h2>
              <TaskForm disabled={dashboardPending} onSubmit={handleCreateTask} />
              <TaskFilters value={filters} onChange={setFilters} />
            </section>
            <TaskBoard
              tasks={visibleTasks}
              onStatusChange={handleStatusChange}
              onDeleteTask={handleDeleteTask}
              onUpdateTask={handleUpdateTask}
            />
          </>
        )}
      </main>
    </AppShell>
  );
}
