import { apiRequest } from "../../api/client";
import type { Project } from "../../types";

type ProjectListData = {
  projects?: Project[];
};

type ProjectData = {
  project?: Project;
};

export async function listProjects() {
  const data = await apiRequest<ProjectListData | Project[]>("/api/projects");
  if (Array.isArray(data)) {
    return data;
  }
  return data.projects ?? [];
}

export async function createProject(name: string) {
  const data = await apiRequest<ProjectData | Project>("/api/projects", {
    method: "POST",
    body: JSON.stringify({ name })
  });

  if (data && typeof data === "object" && "id" in data) {
    return data;
  }
  if (!data.project) {
    throw new Error("Project creation response missing project data.");
  }
  return data.project;
}

export async function updateProject(projectId: string, name: string) {
  const data = await apiRequest<ProjectData | Project>(`/api/projects/${projectId}`, {
    method: "PATCH",
    body: JSON.stringify({ name })
  });

  if (data && typeof data === "object" && "id" in data) {
    return data;
  }
  if (!data.project) {
    throw new Error("Project update response missing project data.");
  }
  return data.project;
}

export async function deleteProject(projectId: string) {
  await apiRequest<null>(`/api/projects/${projectId}`, {
    method: "DELETE"
  });
}
